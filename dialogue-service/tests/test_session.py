"""Session and round-lifecycle tests.

The distinction these protect is the one the architecture document insists on:
stopping playback and stopping inference are two different things
(docs/constraints.md #7).
"""

from __future__ import annotations

import asyncio
import json

from app import protocol
from app.config import Config
from app.protocol import AudioFrame, AudioKind, InterruptReason, State
from tests.support import control_types, drain, make_engines, make_session


def test_round_ids_start_at_one_and_increase() -> None:
    session = make_session(Config())
    assert session.new_round().id == 1
    assert session.new_round().id == 2


async def test_interrupt_drains_the_outbox_then_announces() -> None:
    """Queued stale audio must not delay the interrupt — that is what makes
    barge-in feel immediate."""
    session = make_session(Config())
    session.new_round()
    await session.emit_json({"type": "llm.delta", "text": "x"})
    await session.emit_audio(AudioFrame(AudioKind.TTS, 1, 0, 24000, 1, 20, b"\x00\x00"))

    await session.interrupt(InterruptReason.USER_SPEECH)

    items = drain(session.out)
    assert len(items) == 1
    assert json.loads(items[0])["type"] == "interrupt"
    assert json.loads(items[0])["reason"] == "user_speech"


async def test_interrupt_invalidates_tts_and_marks_the_round() -> None:
    engines = make_engines()
    session = make_session(Config(), engines)
    round_ = session.new_round()
    epoch_before = engines.tts._epoch

    await session.interrupt(InterruptReason.USER_SPEECH)

    assert round_.cancelled
    assert engines.tts._epoch > epoch_before


async def test_new_utterance_after_a_finished_round_is_not_an_interrupt() -> None:
    session = make_session(Config())
    first = session.new_round()
    first.finished = True

    second = await session.on_speech_start()

    assert second.id != first.id
    assert "interrupt" not in control_types(drain(session.out))


async def test_new_utterance_during_a_reply_is_an_interrupt() -> None:
    session = make_session(Config())
    session.new_round()

    second = await session.on_speech_start()

    assert second.id == 2
    assert control_types(drain(session.out)) == ["interrupt"]


async def test_superseded_round_is_not_narrated() -> None:
    session = make_session(Config())
    round_ = session.new_round()
    round_.cancel.set()

    await session.set_state(State.SPEAKING, round_)
    assert drain(session.out) == []

    await session.set_state(State.LISTENING, round_)
    assert control_types(drain(session.out)) == ["state"]


def test_is_current_follows_the_current_round() -> None:
    session = make_session(Config())
    first = session.new_round()
    assert session.is_current(first)

    session.new_round()
    assert not session.is_current(first)


async def test_history_is_bounded_and_feeds_the_next_request() -> None:
    config = Config()
    config.session.max_history_turns = 2
    session = make_session(config)

    for i in range(5):
        session.record_turn(f"u{i}", f"a{i}")

    messages = session.build_messages("now")
    assert len(messages) == 5  # 2 turns of history + the new user message
    assert messages[-1] == {"role": "user", "content": "now"}
    assert messages[0]["content"] == "u3"


def test_empty_assistant_text_is_not_recorded() -> None:
    session = make_session(Config())
    session.record_turn("hello", "")
    assert session.build_messages("x") == [{"role": "user", "content": "x"}]


async def test_close_stops_the_task_and_clears_state() -> None:
    session = make_session(Config())
    session.new_round()
    session.record_turn("a", "b")

    await session.close()

    assert session.current_round is None
    assert session.build_messages("x") == [{"role": "user", "content": "x"}]
    assert not session.is_current(session.new_round())


async def test_cancelling_a_running_pipeline_task_is_clean() -> None:
    """``_cancel_task`` must swallow the cancellation, not propagate it."""
    session = make_session(Config())
    started = asyncio.Event()

    async def long_running() -> None:
        started.set()
        await asyncio.sleep(30)

    session._task = asyncio.create_task(long_running())
    await started.wait()

    await session._cancel_task()

    assert session._task is None
