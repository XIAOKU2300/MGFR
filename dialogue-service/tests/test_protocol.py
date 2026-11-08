"""Wire-format tests.

The byte layout is a contract with the Unity client. These tests are the cheapest
place to catch a change that would silently break it.
"""

from __future__ import annotations

import json

import pytest

from app import protocol
from app.protocol import AudioFrame, AudioKind, ErrorCode, FinishReason, InterruptReason, State


def test_header_is_24_bytes() -> None:
    assert protocol.HEADER_SIZE == 24


def test_audio_frame_round_trip() -> None:
    frame = AudioFrame(
        kind=AudioKind.TTS,
        round=7,
        seq=42,
        sample_rate=32000,
        channels=1,
        frame_ms=20,
        payload=b"\x01\x02" * 320,
    )
    assert protocol.decode_audio_frame(protocol.encode_audio_frame(frame)) == frame


def test_sample_count_counts_samples_not_bytes() -> None:
    frame = AudioFrame(AudioKind.MIC, 1, 0, 16000, 1, 20, b"\x00\x00" * 320)
    assert frame.sample_count == 320


def test_encode_rejects_odd_payload() -> None:
    frame = AudioFrame(AudioKind.MIC, 1, 0, 16000, 1, 20, b"\x00\x01\x02")
    with pytest.raises(protocol.ProtocolError):
        protocol.encode_audio_frame(frame)


def test_encode_rejects_round_out_of_range() -> None:
    frame = AudioFrame(AudioKind.MIC, 2**32, 0, 16000, 1, 20, b"")
    with pytest.raises(protocol.ProtocolError):
        protocol.encode_audio_frame(frame)


def test_decode_rejects_short_frame() -> None:
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_audio_frame(b"\x00" * 8)


def test_decode_rejects_wrong_version() -> None:
    good = protocol.encode_audio_frame(AudioFrame(AudioKind.MIC, 1, 0, 16000, 1, 20, b""))
    bad = bytes([protocol.PROTOCOL_VERSION + 1]) + good[1:]
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_audio_frame(bad)


def test_decode_rejects_unknown_kind() -> None:
    good = protocol.encode_audio_frame(AudioFrame(AudioKind.MIC, 1, 0, 16000, 1, 20, b""))
    bad = good[:1] + bytes([99]) + good[2:]
    with pytest.raises(protocol.ProtocolError):
        protocol.decode_audio_frame(bad)


def test_dumps_keeps_chinese_literal() -> None:
    text = protocol.dumps(protocol.asr_final(1, "你好，我是祀。"))
    assert "你好，我是祀。" in text
    assert "\\u" not in text


def test_state_message_carries_round_and_value() -> None:
    msg = protocol.state(3, State.SPEAKING, "detail")
    assert msg["round"] == 3
    assert msg["state"] == "speaking"
    assert msg["detail"] == "detail"
    assert msg["v"] == protocol.PROTOCOL_VERSION


def test_hello_ack_allows_unknown_sample_rate() -> None:
    """0 is the documented "not known yet" value — the client must not assume one."""
    msg = protocol.hello_ack(
        server_version="0.1.0",
        tts_sample_rate=0,
        tts_channels=1,
        engines={"tts": "gptsovits"},
        max_concurrent_tts=1,
        round_=0,
    )
    assert msg["audio"]["ttsSampleRate"] == 0
    assert msg["audio"]["sampleFormat"] == "s16le"
    assert msg["audio"]["container"] == "raw"
    assert msg["round"] == 0


def test_error_recoverability_defaults() -> None:
    assert protocol.error(1, ErrorCode.INTERNAL, "boom")["recoverable"] is False
    assert protocol.error(1, ErrorCode.BAD_FRAME, "boom")["recoverable"] is True
    assert protocol.error(1, ErrorCode.INTERNAL, "boom", recoverable=True)["recoverable"] is True


def test_loads_accepts_a_well_formed_message() -> None:
    msg = protocol.loads('{"v":1,"type":"interrupt","round":4}')
    assert msg.type == "interrupt"
    assert msg.round == 4


def test_loads_is_lenient_about_unknown_fields() -> None:
    msg = protocol.loads('{"v":1,"type":"ping","t":9,"futureField":{"a":1}}')
    assert msg.type == "ping"
    assert msg.round is None


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '"a string"',
        "[1,2,3]",
        '{"type":"ping"}',  # missing version
        '{"v":99,"type":"ping"}',  # wrong version
        '{"v":1}',  # missing type
        '{"v":1,"type":""}',  # empty type
        '{"v":1,"type":"ping","round":"1"}',  # round must be an int
        '{"v":1,"type":"ping","round":true}',  # bool is not an int here
    ],
)
def test_loads_rejects_malformed_messages(raw: str) -> None:
    with pytest.raises(protocol.ProtocolError):
        protocol.loads(raw)


def test_interrupt_reason_round_trips() -> None:
    msg = protocol.interrupt(5, InterruptReason.USER_SPEECH)
    assert msg["reason"] == "user_speech"
    assert json.loads(protocol.dumps(msg))["round"] == 5


def test_tts_start_reports_the_observed_format() -> None:
    msg = protocol.tts_start(2, 0, "你好。", sample_rate=32000, channels=1)
    assert msg["audio"]["sampleRate"] == 32000
    assert msg["sentenceIndex"] == 0


def test_tts_end_reason() -> None:
    assert protocol.tts_end(2, 1, FinishReason.ERROR)["reason"] == "error"
