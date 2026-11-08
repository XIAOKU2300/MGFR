"""Wire protocol between the Unity client and the dialogue service.

This module is the single source of truth for the byte layout and the control
message vocabulary. ``docs/protocol.md`` documents the same thing for humans;
the two must be changed together.

Two frame kinds share one WebSocket: JSON text frames for control, binary frames
for PCM audio. Sharing one socket is deliberate — it means the transport
preserves ordering between control and audio, which is what makes discarding
late audio by round id reliable (see docs/constraints.md #7).
"""

from __future__ import annotations

import json
import struct
import time
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any

PROTOCOL_VERSION = 1

# ---------------------------------------------------------------------------
# Binary audio frames
# ---------------------------------------------------------------------------

# version, kind, flags, round, seq, sample_rate, channels, frame_ms
_HEADER = struct.Struct("<BBHIQIHH")
HEADER_SIZE = _HEADER.size
assert HEADER_SIZE == 24, f"header must be 24 bytes, got {HEADER_SIZE}"

#: v1 is S16LE only. Changing this is a protocol version change, not a new field.
SAMPLE_FORMAT = "s16le"

#: No container is ever sent over the wire — the service strips it server-side.
CONTAINER = "raw"


class AudioKind(IntEnum):
    MIC = 1
    TTS = 2


@dataclass(slots=True)
class AudioFrame:
    """One binary WebSocket frame carrying PCM audio."""

    kind: AudioKind
    round: int
    seq: int
    sample_rate: int
    channels: int
    frame_ms: int
    payload: bytes  # interleaved S16LE

    @property
    def sample_count(self) -> int:
        """Number of int16 samples in the payload, across all channels."""
        return len(self.payload) // 2


class ProtocolError(Exception):
    """A malformed frame or control message."""


def encode_audio_frame(frame: AudioFrame, *, version: int = PROTOCOL_VERSION) -> bytes:
    """Serialise an :class:`AudioFrame` to bytes."""
    if not 0 <= frame.round <= 0xFFFFFFFF:
        raise ProtocolError(f"round out of range: {frame.round}")
    if not 0 <= frame.seq <= 0xFFFFFFFFFFFFFFFF:
        raise ProtocolError(f"seq out of range: {frame.seq}")
    if len(frame.payload) % 2:
        raise ProtocolError("S16LE payload must have an even length")
    return (
        _HEADER.pack(
            version,
            int(frame.kind),
            0,  # flags, reserved
            frame.round,
            frame.seq,
            frame.sample_rate,
            frame.channels,
            frame.frame_ms,
        )
        + frame.payload
    )


def decode_audio_frame(buf: bytes) -> AudioFrame:
    """Parse bytes received on the socket into an :class:`AudioFrame`."""
    if len(buf) < HEADER_SIZE:
        raise ProtocolError(f"frame shorter than {HEADER_SIZE} bytes: {len(buf)}")
    version, kind, _flags, round_, seq, rate, channels, frame_ms = _HEADER.unpack_from(buf, 0)
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported frame version {version}")
    try:
        kind_enum = AudioKind(kind)
    except ValueError as exc:
        raise ProtocolError(f"unknown audio kind {kind}") from exc
    payload = buf[HEADER_SIZE:]
    if len(payload) % 2:
        raise ProtocolError("S16LE payload must have an even length")
    return AudioFrame(kind_enum, round_, seq, rate, channels, frame_ms, payload)


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


class State(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    RECOGNIZING = "recognizing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class ErrorCode(str, Enum):
    PROTOCOL_VERSION = "PROTOCOL_VERSION"
    BAD_FRAME = "BAD_FRAME"
    ROUND_STALE = "ROUND_STALE"
    ENGINE_UNAVAILABLE = "ENGINE_UNAVAILABLE"
    ASR_FAILED = "ASR_FAILED"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    TTS_UNAVAILABLE = "TTS_UNAVAILABLE"
    INTERNAL = "INTERNAL"


#: Whether the client may keep the session alive after this error.
RECOVERABLE: dict[ErrorCode, bool] = {
    ErrorCode.PROTOCOL_VERSION: False,
    ErrorCode.BAD_FRAME: True,
    ErrorCode.ROUND_STALE: True,
    ErrorCode.ENGINE_UNAVAILABLE: True,
    ErrorCode.ASR_FAILED: True,
    ErrorCode.LLM_UNAVAILABLE: True,
    ErrorCode.TTS_UNAVAILABLE: True,
    ErrorCode.INTERNAL: False,
}


class InterruptReason(str, Enum):
    USER_SPEECH = "user_speech"
    CLIENT_REQUEST = "client_request"
    SESSION_END = "session_end"


class FinishReason(str, Enum):
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Control messages — outbound
# ---------------------------------------------------------------------------


def _envelope(msg_type: str, round_: int | None = None, **fields: Any) -> dict[str, Any]:
    msg: dict[str, Any] = {"v": PROTOCOL_VERSION, "type": msg_type, "ts": time.time()}
    if round_ is not None:
        msg["round"] = round_
    msg.update(fields)
    return msg


def dumps(msg: dict[str, Any]) -> str:
    """Serialise a control message. Chinese text is kept literal, not \\u-escaped."""
    return json.dumps(msg, ensure_ascii=False, separators=(",", ":"))


def hello_ack(
    *,
    server_version: str,
    tts_sample_rate: int,
    tts_channels: int,
    engines: dict[str, str],
    max_concurrent_tts: int,
    round_: int,
) -> dict[str, Any]:
    """Handshake reply.

    ``tts_sample_rate`` is ``0`` when it is not yet known; the real value is then
    announced on each ``tts.start``. The client must never assume a fixed rate.
    """
    return _envelope(
        "hello.ack",
        round_,
        serverVersion=server_version,
        audio={
            "ttsSampleRate": tts_sample_rate,
            "ttsChannels": tts_channels,
            "sampleFormat": SAMPLE_FORMAT,
            "container": CONTAINER,
        },
        engines=engines,
        limits={"maxConcurrentTts": max_concurrent_tts},
    )


def state(round_: int, value: State, detail: str | None = None) -> dict[str, Any]:
    return _envelope("state", round_, state=value.value, detail=detail)


def asr_partial(round_: int, text: str) -> dict[str, Any]:
    return _envelope("asr.partial", round_, text=text)


def asr_final(round_: int, text: str) -> dict[str, Any]:
    return _envelope("asr.final", round_, text=text)


def llm_delta(round_: int, text: str) -> dict[str, Any]:
    return _envelope("llm.delta", round_, text=text)


def llm_done(round_: int, finish_reason: FinishReason) -> dict[str, Any]:
    return _envelope("llm.done", round_, finishReason=finish_reason.value)


def tts_start(
    round_: int,
    sentence_index: int,
    text: str,
    *,
    sample_rate: int,
    channels: int,
) -> dict[str, Any]:
    """Sent immediately before the first audio frame of a sentence.

    The rate here comes from the actual GPT-SoVITS response, not from config.
    """
    return _envelope(
        "tts.start",
        round_,
        sentenceIndex=sentence_index,
        text=text,
        audio={
            "sampleRate": sample_rate,
            "channels": channels,
            "sampleFormat": SAMPLE_FORMAT,
            "container": CONTAINER,
        },
    )


def tts_end(round_: int, sentence_index: int, reason: FinishReason) -> dict[str, Any]:
    return _envelope("tts.end", round_, sentenceIndex=sentence_index, reason=reason.value)


def interrupt(round_: int, reason: InterruptReason) -> dict[str, Any]:
    return _envelope("interrupt", round_, reason=reason.value)


def error(
    round_: int | None,
    code: ErrorCode,
    message: str,
    recoverable: bool | None = None,
) -> dict[str, Any]:
    if recoverable is None:
        recoverable = RECOVERABLE[code]
    return _envelope("error", round_, code=code.value, message=message, recoverable=recoverable)


def pong(t: Any) -> dict[str, Any]:
    return _envelope("pong", None, t=t)


# ---------------------------------------------------------------------------
# Control messages — inbound
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ControlMessage:
    """A parsed inbound control message.

    Inbound parsing is deliberately lenient about unknown fields but strict about
    the version and the presence of ``type``, so a future client addition does not
    tear down the socket.
    """

    type: str
    round: int | None
    payload: dict[str, Any]


def loads(text: str) -> ControlMessage:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ProtocolError("control message must be a JSON object")

    version = obj.get("v")
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version {version!r}")

    msg_type = obj.get("type")
    if not isinstance(msg_type, str) or not msg_type:
        raise ProtocolError("control message is missing 'type'")

    round_ = obj.get("round")
    if round_ is not None and (not isinstance(round_, int) or isinstance(round_, bool)):
        raise ProtocolError("'round' must be an integer")

    return ControlMessage(msg_type, round_, obj)
