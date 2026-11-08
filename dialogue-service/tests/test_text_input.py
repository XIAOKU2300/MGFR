"""``text.input`` — typed text standing in for a recognised utterance.

The point of this message is that a typed line takes exactly the path a spoken
one does once recognition has finished: a round is allocated the same way, the
LLM streams, TTS streams back, and an ``interrupt`` stops it like any other turn.
"""

from __future__ import annotations

import asyncio
import contextlib
import json

import pytest

from app import protocol
from app.config import Config
from app.engines.stub import StubLlm, StubTts
from app.main import Connection, _HANDLERS, _handle_text_input
from app.pipeline import run_text_round
from app.protocol import AudioKind, ErrorCode, InterruptReason, State
from tests.support import control_types, drain, make_engines, make_session, wait_until


def test_text_input_parses_in_the_documented_wire_format() -> None:
    msg = protocol.loads('{"v":1,"type":"text.input","ts":1730000000.0,"text":"你好呀"}')
    assert msg.type == "text.input"
    assert msg.round is None  # a typed line carries no round of its own
    assert msg.payload["text"] == "你好呀"


def test_text_input_is_registered() -> None:
    assert "text.input" in _HANDLERS


async def test_run_text_round_emits_the_documented_sequence() -> None:
    session = make_session(Config())
    round_ = session.new_round()

    await run_text_round(session, round_, "你好呀")

    items = drain(session.out)
    types = control_types(items)
    assert "asr.final" in types
    assert types.count("llm.delta") > 0
    assert "llm.done" in types
    assert "tts.start" in types
    assert "tts.end" in types
    assert round_.finished
    assert round_.user_text == "你好呀"
    assert round_.assistant_text

    audio = [i for i in items if isinstance(i, bytes)]
    assert audio
    frame = protocol.decode_audio_frame(audio[0])
    assert frame.kind is AudioKind.TTS
    assert frame.round == round_.id


async def test_a_text_round_skips_recognition_but_not_the_reply() -> None:
    """No ASR runs, so no ``recognizing`` state — straight to thinking."""
    session = make_session(Config())
    round_ = session.new_round()

    await run_text_round(session, round_, "你好呀")

    states = [
        protocol.loads(i).payload["state"]
        for i in drain(session.out)
        if isinstance(i, str) and protocol.loads(i).type == "state"
    ]
    assert State.RECOGNIZING.value not in states
    assert states == [State.THINKING.value, State.SPEAKING.value, State.LISTENING.value]


async def test_a_text_round_records_history_like_a_spoken_turn() -> None:
    session = make_session(Config())
    round_ = session.new_round()

    await run_text_round(session, round_, "你好呀")

    messages = session.build_messages("next")
    assert messages[0] == {"role": "user", "content": "你好呀"}
    assert messages[1]["role"] == "assistant"


async def test_begin_text_turn_allocates_a_round_and_runs_it() -> None:
    session = make_session(Config())
    session.new_round()  # round 1

    round_ = await session.begin_text_turn("你好呀")
    assert round_.id == 2

    task = session._task
    assert task is not None
    await asyncio.wait_for(task, timeout=5.0)

    types = control_types(drain(session.out))
    assert "llm.delta" in types
    assert "tts.end" in types
    assert round_.finished


async def test_a_text_turn_during_a_reply_interrupts_the_previous_round() -> None:
    session = make_session(Config())
    session.new_round()  # an unfinished round

    await session.begin_text_turn("新的输入")

    types = control_types(drain(session.out))
    assert "interrupt" in types
    assert session.current_round is not None
    assert session.current_round.id == 2
    await session._cancel_task()


async def test_interrupting_a_text_turn_stops_its_audio() -> None:
    reply = "这是一句刻意写得很长的回答，用来确认打断之后不会再有任何音频被发送出去。"
    engines = make_engines(
        llm=StubLlm(reply=reply, token_delay_s=0.0),
        tts=StubTts(realtime=True),
    )
    session = make_session(Config(), engines)

    round_ = await session.begin_text_turn("给我讲一个很长的故事")
    task = session._task
    assert task is not None
    assert await wait_until(lambda: round_.tts_seq > 0), "the reply never started speaking"

    await session.interrupt(InterruptReason.USER_SPEECH)
    drain(session.out)

    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=5.0)
    # Give anything that was going to leak a chance to leak.
    await asyncio.sleep(0.3)
    assert drain(session.out) == []
    assert round_.cancelled
    assert not round_.finished


# -- handler level: graceful handling of a bad ``text`` ----------------------


def _conn() -> Connection:
    conn = Connection(ws=None, config=Config(), engines=make_engines())
    conn.started = True
    return conn


@pytest.mark.parametrize(
    "raw",
    [
        '{"v":1,"type":"text.input","ts":1}',  # no text field
        '{"v":1,"type":"text.input","ts":1,"text":""}',  # empty
        '{"v":1,"type":"text.input","ts":1,"text":"   "}',  # whitespace only
        '{"v":1,"type":"text.input","ts":1,"text":123}',  # not a string
    ],
)
async def test_blank_text_is_a_recoverable_error_and_allocates_no_round(raw: str) -> None:
    conn = _conn()

    await _handle_text_input(conn, protocol.loads(raw))

    items = drain(conn.session.out)
    assert control_types(items) == ["error"]
    msg = json.loads(items[0])
    assert msg["code"] == ErrorCode.BAD_FRAME.value
    assert msg["recoverable"] is True
    assert conn.session.current_round is None


async def test_a_valid_text_input_runs_a_full_turn() -> None:
    conn = _conn()

    await _handle_text_input(
        conn, protocol.loads('{"v":1,"type":"text.input","ts":1,"text":"你好呀"}')
    )

    round_ = conn.session.current_round
    assert round_ is not None
    task = conn.session._task
    assert task is not None
    await asyncio.wait_for(task, timeout=5.0)

    types = control_types(drain(conn.session.out))
    assert "asr.final" in types
    assert "llm.delta" in types
    assert "llm.done" in types
    assert "tts.start" in types
    assert "tts.end" in types
    assert round_.user_text == "你好呀"
    assert round_.finished
