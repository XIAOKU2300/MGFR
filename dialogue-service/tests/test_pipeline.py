"""Pipeline tests — the full round, and what an interruption does to it."""

from __future__ import annotations

import asyncio

import numpy as np

from app import protocol
from app.config import Config
from app.engines.stub import StubLlm, StubTts
from app.pipeline import run_round
from app.protocol import AudioKind, InterruptReason, State
from tests.support import control_types, drain, make_engines, make_session, wait_until

UTTERANCE = np.zeros(16000, dtype=np.float32)


async def test_a_round_emits_the_documented_sequence() -> None:
    session = make_session(Config())
    round_ = session.new_round()

    await run_round(session, round_, UTTERANCE, 16000)

    items = drain(session.out)
    types = control_types(items)

    assert types[0] == "state"  # recognizing
    assert "asr.final" in types
    assert types.count("llm.delta") > 0
    assert "llm.done" in types
    assert "tts.start" in types
    assert "tts.end" in types
    assert types[-1] == "state"
    assert round_.finished
    assert round_.user_text
    assert round_.assistant_text

    # Audio frames are binary, not JSON, and carry the round id.
    audio = [i for i in items if isinstance(i, bytes)]
    assert audio
    frame = protocol.decode_audio_frame(audio[0])
    assert frame.kind is AudioKind.TTS
    assert frame.round == round_.id


async def test_states_advance_in_order() -> None:
    session = make_session(Config())
    round_ = session.new_round()

    await run_round(session, round_, UTTERANCE, 16000)

    states = [
        protocol.loads(i).payload["state"]
        for i in drain(session.out)
        if isinstance(i, str) and protocol.loads(i).type == "state"
    ]
    assert states == [
        State.RECOGNIZING.value,
        State.THINKING.value,
        State.SPEAKING.value,
        State.LISTENING.value,
    ]


async def test_tts_start_precedes_its_audio() -> None:
    """The client must learn the format before the first frame of a sentence."""
    session = make_session(Config())
    round_ = session.new_round()

    await run_round(session, round_, UTTERANCE, 16000)

    items = drain(session.out)
    first_audio = next(i for i, item in enumerate(items) if isinstance(item, bytes))
    first_start = next(
        i
        for i, item in enumerate(items)
        if isinstance(item, str) and protocol.loads(item).type == "tts.start"
    )
    assert first_start < first_audio


async def test_the_history_grows_by_one_turn() -> None:
    session = make_session(Config())
    round_ = session.new_round()

    await run_round(session, round_, UTTERANCE, 16000)

    messages = session.build_messages("next")
    assert len(messages) == 3  # user + assistant + the new user message
    assert messages[1]["role"] == "assistant"


async def test_an_empty_utterance_produces_no_reply() -> None:
    engines = make_engines()
    engines.asr.transcribe = _empty_transcribe  # type: ignore[method-assign]
    session = make_session(Config(), engines)
    round_ = session.new_round()

    await run_round(session, round_, UTTERANCE, 16000)

    types = control_types(drain(session.out))
    assert "asr.final" not in types
    assert "llm.delta" not in types
    assert round_.finished


async def _empty_transcribe(samples, sample_rate) -> str:
    return ""


async def test_interruption_stops_the_audio_immediately() -> None:
    """After an interrupt, nothing more may be emitted for the dead round."""
    reply = "这是一句刻意写得很长的句子，用来确认打断之后不会再有任何音频被发送出去。"
    engines = make_engines(
        llm=StubLlm(reply=reply, token_delay_s=0.0),
        tts=StubTts(realtime=True),
    )
    session = make_session(Config(), engines)
    round_ = session.new_round()

    task = asyncio.create_task(run_round(session, round_, UTTERANCE, 16000))
    assert await wait_until(lambda: round_.tts_seq > 0), "the reply never started speaking"

    await session.interrupt(InterruptReason.USER_SPEECH)
    drain(session.out)

    await asyncio.wait_for(task, timeout=5.0)

    # Give anything that was going to leak a chance to leak.
    await asyncio.sleep(0.3)
    assert drain(session.out) == []
    assert round_.cancelled
    assert not round_.finished


async def test_a_superseded_round_does_not_record_history() -> None:
    engines = make_engines(
        llm=StubLlm(reply="一段比较长的回答，用来制造一个可以被打断的窗口。", token_delay_s=0.0),
        tts=StubTts(realtime=True),
    )
    session = make_session(Config(), engines)
    round_ = session.new_round()

    task = asyncio.create_task(run_round(session, round_, UTTERANCE, 16000))
    assert await wait_until(lambda: round_.tts_seq > 0)

    await session.interrupt(InterruptReason.USER_SPEECH)
    await asyncio.wait_for(task, timeout=5.0)

    assert session.build_messages("next") == [{"role": "user", "content": "next"}]
