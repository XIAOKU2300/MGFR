"""Orchestration for one round: ASR → LLM → sentence split → TTS.

Two rules shape this file:

* **Cancellation is checked at every yield point.** A superseded round stops as
  soon as it notices, rather than finishing work whose output will be thrown away.
* **TTS failure does not lose the text.** The LLM deltas have already been sent by
  the time synthesis runs, so a synthesis error degrades to text-only rather than
  silence (docs/constraints.md #7).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable

import numpy as np

from . import protocol
from .engines.base import EngineUnavailable
from .protocol import AudioFrame, AudioKind, ErrorCode, FinishReason, State
from .session import Round, Session
from .text import SentenceAccumulator, normalize_for_speech

logger = logging.getLogger(__name__)


async def run_round(session: Session, round_: Round, utterance: np.ndarray, sample_rate: int) -> None:
    """Drive one round from microphone audio. Safe to cancel at any point."""
    await _drive_round(session, round_, lambda: _recognize(session, round_, utterance, sample_rate))


async def run_text_round(session: Session, round_: Round, text: str) -> None:
    """Drive one round from typed text, skipping ASR.

    The text stands in for a recognition result, so the round goes straight to
    the LLM and TTS. Everything after that — cancellation, state transitions,
    history — is identical to ``run_round``.
    """
    await _drive_round(session, round_, lambda: _accept_text(session, round_, text))


async def _drive_round(
    session: Session, round_: Round, recognize: "Callable[[], Awaitable[str | None]]"
) -> None:
    """Shared round body: obtain the user's text, then think, speak and finish.

    ``recognize`` is a zero-argument callable returning the user's text, or
    ``None`` when the round should stop without a reply. It is a callable rather
    than a coroutine so that a round cancelled before it starts does not leave an
    un-awaited coroutine behind.
    """
    try:
        text = await recognize()
        if text is None:
            return
        if not await _think_and_speak(session, round_, text):
            return
        round_.finished = True
        session.record_turn(round_.user_text, round_.assistant_text)
        await session.set_state(State.LISTENING, round_)
    except asyncio.CancelledError:
        raise
    except EngineUnavailable as exc:
        logger.warning("round %s: engine unavailable: %s", round_.id, exc)
        await session.emit_json(
            protocol.error(round_.id, ErrorCode.ENGINE_UNAVAILABLE, str(exc))
        )
        await session.set_state(State.ERROR, round_, str(exc))
    except Exception as exc:  # noqa: BLE001 - never take the connection down
        logger.exception("round %s failed", round_.id)
        await session.emit_json(protocol.error(round_.id, ErrorCode.INTERNAL, str(exc)))
        await session.set_state(State.ERROR, round_, str(exc))


async def _recognize(
    session: Session, round_: Round, utterance: np.ndarray, sample_rate: int
) -> str | None:
    """Return recognised text, or None if the round should stop."""
    await session.set_state(State.RECOGNIZING, round_)
    try:
        recognition_started = time.perf_counter()
        text = await session.engines.asr.transcribe(utterance, sample_rate)
        await session.emit_json({"v":1,"type":"latency","round":round_.id,"stage":"asr","processingMs":round((time.perf_counter()-recognition_started)*1000,2)})
    except EngineUnavailable as exc:
        await session.emit_json(protocol.error(round_.id, ErrorCode.ENGINE_UNAVAILABLE, str(exc)))
        await session.set_state(State.ERROR, round_, str(exc))
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("round %s: ASR failed", round_.id)
        await session.emit_json(protocol.error(round_.id, ErrorCode.ASR_FAILED, str(exc)))
        await session.set_state(State.LISTENING, round_)
        return None

    if not session.is_current(round_):
        return None

    text = (text or "").strip()
    round_.user_text = text
    if not text:
        # Nothing intelligible — go back to listening without replying.
        round_.finished = True
        await session.set_state(State.LISTENING, round_, "empty utterance")
        return None

    await session.emit_json(protocol.asr_final(round_.id, text))
    return text


async def _accept_text(session: Session, round_: Round, text: str) -> str | None:
    """Accept typed text in place of a recognition result.

    Mirrors ``_recognize``'s contract: return the user's text, or ``None`` when
    the round should stop. There is no recognition step, so no ``recognizing``
    state is announced; the text is reported as ``asr.final`` so that everything
    downstream — the client's transcript, history, sentence splitting — is
    unchanged from a spoken turn.
    """
    if not session.is_current(round_):
        return None
    text = (text or "").strip()
    if not text:
        round_.finished = True
        await session.set_state(State.LISTENING, round_, "empty text")
        return None
    round_.user_text = text
    await session.emit_json(protocol.asr_final(round_.id, text))
    return text


async def _think_and_speak(session: Session, round_: Round, user_text: str) -> bool:
    """Stream the reply and speak it sentence by sentence.

    Returns False if the round was superseded.
    """
    await session.set_state(State.THINKING, round_)
    messages = session.build_messages(user_text)
    accumulator = SentenceAccumulator(max_chars=64, min_chars=12)

    queue: asyncio.Queue = asyncio.Queue(maxsize=4)

    async def collect_text():
        try:
            async for delta in session.engines.llm.stream(messages, round_.cancel):
                if not session.is_current(round_):
                    return
                round_.assistant_text += delta
                await session.emit_json(protocol.llm_delta(round_.id, delta))
                for sentence in accumulator.push(delta):
                    await queue.put(sentence)
            if not session.is_current(round_):
                return
            for sentence in accumulator.flush():
                await queue.put(sentence)
            metrics = getattr(session.engines.llm, "metrics", None)
            if metrics:
                await session.emit_json({"v":1,"type":"latency","round":round_.id,"stage":"llm",**metrics})
            await session.emit_json(protocol.llm_done(round_.id, FinishReason.COMPLETED))
        except Exception as error:
            await queue.put(error)
            return
        await queue.put(None)

    producer = asyncio.create_task(collect_text())
    index = 0
    try:
        while session.is_current(round_):
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                if not isinstance(item, EngineUnavailable):
                    raise item
                await session.emit_json(protocol.error(round_.id, ErrorCode.LLM_UNAVAILABLE, str(item)))
                await session.set_state(State.ERROR, round_, str(item))
                return False
            if index == 0:
                await session.set_state(State.SPEAKING, round_)
            await _speak(session, round_, item, index)
            index += 1
    finally:
        producer.cancel()
        await asyncio.gather(producer, return_exceptions=True)

    if not session.is_current(round_):
        return False
    await session.emit_json({"v": 1, "type": "audio.done", "round": round_.id})
    return True


async def _speak(session: Session, round_: Round, sentence: str, index: int) -> None:
    """Synthesise one sentence and stream it to the client as PCM frames."""
    sentence = normalize_for_speech(sentence)
    if not sentence or not session.is_current(round_):
        return

    started = False
    synthesis_started = time.perf_counter()
    try:
        async for chunk in session.engines.tts.synthesize(sentence, round_.cancel):
            if not session.is_current(round_):
                return
            if not started:
                await session.emit_json({"v":1,"type":"latency","round":round_.id,"stage":"tts","sentenceIndex":index,"firstAudioMs":round((time.perf_counter()-synthesis_started)*1000,2)})
                # Announce the format only once we have it — the rate comes from
                # the actual response, not from configuration.
                await session.emit_json(
                    protocol.tts_start(
                        round_.id,
                        index,
                        sentence,
                        sample_rate=chunk.sample_rate,
                        channels=chunk.channels,
                    )
                )
                started = True
            await session.emit_audio(
                AudioFrame(
                    kind=AudioKind.TTS,
                    round=round_.id,
                    seq=session.next_tts_seq(round_),
                    sample_rate=chunk.sample_rate,
                    channels=chunk.channels,
                    frame_ms=_frame_ms(chunk.pcm, chunk.channels, chunk.sample_rate),
                    payload=chunk.pcm,
                )
            )
    except EngineUnavailable as exc:
        logger.warning("round %s: TTS unavailable: %s", round_.id, exc)
        await session.emit_json(
            protocol.error(round_.id, ErrorCode.TTS_UNAVAILABLE, str(exc))
        )
        if started:
            await session.emit_json(protocol.tts_end(round_.id, index, FinishReason.ERROR))
        return

    if started and session.is_current(round_):
        await session.emit_json(protocol.tts_end(round_.id, index, FinishReason.COMPLETED))


def _frame_ms(pcm: bytes, channels: int, sample_rate: int) -> int:
    samples = len(pcm) // 2
    if channels <= 0 or sample_rate <= 0:
        return 0
    return int(round(samples / channels / sample_rate * 1000.0))
