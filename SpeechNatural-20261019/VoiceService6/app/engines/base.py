"""Engine interfaces.

The pipeline depends on these protocols only, so the stub implementations and the
real ones are interchangeable. Every engine is selected by name in ``config.toml``
under ``[engines]``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import AsyncIterator, Protocol, runtime_checkable

import numpy as np


class EngineUnavailable(RuntimeError):
    """A configured engine cannot be used — missing dependency or missing model.

    Raised loudly rather than degrading silently, so a misconfiguration surfaces
    as an explicit ``ENGINE_UNAVAILABLE`` error on the client instead of a
    character that quietly never answers.
    """


@dataclass(slots=True)
class AudioChunk:
    """A block of synthesised audio, ready to be framed and sent."""

    pcm: bytes  # interleaved S16LE
    sample_rate: int
    channels: int


class VadEvent(Enum):
    NONE = auto()
    SPEECH_START = auto()
    SPEECH_END = auto()


@runtime_checkable
class VadEngine(Protocol):
    """Segments a continuous microphone stream into utterances.

    Stateful and incremental: frames arrive as they are captured.
    """

    def reset(self) -> None:
        """Drop all state, e.g. between sessions."""

    def push(self, frame: np.ndarray, sample_rate: int) -> VadEvent:
        """Feed one mono float32 frame; return the transition it caused, if any."""


@runtime_checkable
class AsrEngine(Protocol):
    """Turns one complete utterance into text."""

    name: str

    async def transcribe(self, samples: np.ndarray, sample_rate: int) -> str:
        """Recognise a mono float32 utterance. Returns ``""`` when unintelligible."""


@runtime_checkable
class LlmEngine(Protocol):
    """Streams assistant text for a conversation."""

    name: str

    def stream(
        self, messages: list[dict[str, str]], cancel: asyncio.Event
    ) -> AsyncIterator[str]:
        """Yield text deltas.

        ``cancel`` is checked between deltas. Setting it must stop the stream
        promptly — it is what makes barge-in feel immediate.
        """


@runtime_checkable
class TtsEngine(Protocol):
    """Synthesises speech for one short sentence.

    Implementations must:
      * serialise synthesis (GPT-SoVITS has no cancellation endpoint);
      * read the sample rate from the actual response, never assume it;
      * never emit a partially written container as if it were complete;
      * discard output whose generation epoch has been superseded.
    """

    name: str

    async def synthesize(self, text: str, cancel: asyncio.Event) -> AsyncIterator[AudioChunk]:
        """Yield PCM chunks for ``text``."""

    def invalidate(self) -> None:
        """Mark in-flight synthesis as stale; its output will be discarded."""
