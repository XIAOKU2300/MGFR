"""Session and round lifecycle.

The service is authoritative on round ids. A round covers one user utterance and
the assistant reply to it. Everything the client receives carries a round id, and
the client drops TTS audio whose round is no longer current — that is the
mechanism that makes late audio from a stale GPT-SoVITS request harmless
(docs/constraints.md #7).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from . import protocol
from .protocol import AudioFrame, ErrorCode, FinishReason, InterruptReason, State

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .config import Config
    from .engines.factory import Engines

logger = logging.getLogger(__name__)


@dataclass
class Round:
    """One user utterance and the reply to it."""

    id: int
    started_at: float = field(default_factory=time.time)
    #: Set when the round is superseded. Engines check it, and the task is cancelled.
    cancel: asyncio.Event = field(default_factory=asyncio.Event)
    user_text: str = ""
    assistant_text: str = ""
    #: True once the reply has been fully delivered. A round that is not finished
    #: is what makes a new speech onset an interruption rather than a new turn.
    finished: bool = False
    tts_seq: int = 0

    @property
    def cancelled(self) -> bool:
        return self.cancel.is_set()


class Session:
    """Per-connection session state. Nothing is persisted; v1 is current-session only."""

    def __init__(self, *, engines: "Engines", config: "Config", out: asyncio.Queue) -> None:
        self.engines = engines
        self.config = config
        self.out = out
        self.current_round: Round | None = None
        self._next_round_id = 1
        self._task: asyncio.Task | None = None
        self._history: list[dict[str, str]] = []
        self._closed = False

    # -- outbound ----------------------------------------------------------

    async def emit_json(self, message: dict[str, Any]) -> None:
        await self.out.put(protocol.dumps(message))

    async def emit_audio(self, frame: AudioFrame) -> None:
        await self.out.put(protocol.encode_audio_frame(frame))

    def drain_outbox(self) -> None:
        """Discard everything queued but not yet written to the socket."""
        while True:
            try:
                self.out.get_nowait()
            except asyncio.QueueEmpty:
                return

    async def set_state(
        self, value: State, round_: Round | None = None, detail: str | None = None
    ) -> None:
        """Announce a state transition.

        A superseded round is not narrated: the client has already been told to
        stop, and a late ``state`` for a dead round would only confuse it.
        """
        target = round_ if round_ is not None else self.current_round
        if target is not None and target.cancelled and value not in (
            State.LISTENING,
            State.IDLE,
            State.ERROR,
        ):
            return
        await self.emit_json(protocol.state(target.id if target else 0, value, detail))

    # -- rounds ------------------------------------------------------------

    def new_round(self) -> Round:
        round_ = Round(id=self._next_round_id)
        self._next_round_id += 1
        self.current_round = round_
        return round_

    def is_current(self, round_: Round) -> bool:
        return (
            not self._closed
            and self.current_round is not None
            and self.current_round.id == round_.id
            and not round_.cancelled
        )

    def next_tts_seq(self, round_: Round) -> int:
        seq = round_.tts_seq
        round_.tts_seq += 1
        return seq

    # -- interruption ------------------------------------------------------

    async def interrupt(self, reason: InterruptReason) -> None:
        """Stop the current round.

        Two separate obligations, deliberately not conflated:

        * the client is told to stop playback and flush its queue, immediately;
        * on this side the TTS generation epoch is invalidated and the pipeline
          task cancelled. GPT-SoVITS keeps computing — its output is discarded.
        """
        round_ = self.current_round
        if round_ is None:
            return
        round_.cancel.set()
        # Flush anything still queued for the dead round *before* announcing the
        # interruption. Otherwise the interrupt message sits behind stale audio and
        # barge-in feels laggy precisely when it needs to feel immediate.
        self.drain_outbox()
        await self.emit_json(protocol.interrupt(round_.id, reason))
        self.engines.tts.invalidate()
        await self._cancel_task()

    async def on_speech_start(self) -> Round:
        """A new utterance has begun.

        If a reply is still being produced, that is an interruption; otherwise this
        is simply the next turn. Either way a fresh round is allocated.
        """
        previous = self.current_round
        if previous is not None and not previous.finished:
            await self.interrupt(InterruptReason.USER_SPEECH)
        self.engines.tts.invalidate()
        return self.new_round()

    # -- pipeline task -----------------------------------------------------

    async def begin_recognition(self, utterance, sample_rate: int) -> None:
        """Run the pipeline for the current round on a cancellable task."""
        from . import pipeline  # imported here to avoid a cycle

        round_ = self.current_round or self.new_round()
        await self._cancel_task()
        self._task = asyncio.create_task(
            pipeline.run_round(self, round_, utterance, sample_rate),
            name=f"round-{round_.id}",
        )

    async def begin_text_turn(self, text: str) -> Round:
        """Start a round from typed text instead of recognised speech.

        Behaves exactly like a speech onset followed by a recognition result: an
        unfinished previous round is interrupted, a fresh round is allocated, and
        the pipeline runs with ``text`` standing in for the ASR output. The
        returned round is the one now in progress.
        """
        from . import pipeline  # imported here to avoid a cycle

        round_ = await self.on_speech_start()
        round_.user_text = text
        await self._cancel_task()
        self._task = asyncio.create_task(
            pipeline.run_text_round(self, round_, text),
            name=f"round-{round_.id}",
        )
        return round_

    async def _cancel_task(self) -> None:
        task = self._task
        self._task = None
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001 - a dying task must not take the session down
            logger.exception("pipeline task raised while being cancelled")

    # -- history -----------------------------------------------------------

    def build_messages(self, user_text: str) -> list[dict[str, str]]:
        return [*self._history, {"role": "user", "content": user_text}]

    def record_turn(self, user_text: str, assistant_text: str) -> None:
        if not assistant_text:
            return
        self._history.append({"role": "user", "content": user_text})
        self._history.append({"role": "assistant", "content": assistant_text})
        # v1 keeps the current session only; bound it so a long chat cannot grow
        # without limit.
        limit = self.config.session.max_history_turns * 2
        if len(self._history) > limit:
            del self._history[: len(self._history) - limit]

    # -- lifecycle ---------------------------------------------------------

    async def reset_for_new_session(self) -> None:
        await self.interrupt(InterruptReason.SESSION_END)
        self._history.clear()
        self.engines.vad.reset()
        self.current_round = None

    async def close(self) -> None:
        self._closed = True
        self.engines.tts.invalidate()
        await self._cancel_task()
        self._history.clear()
        self.current_round = None
