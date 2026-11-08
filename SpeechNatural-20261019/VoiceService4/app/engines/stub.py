"""Stub engines — no models, no GPU, no API key.

These are not placeholders to be thrown away. Stub mode is how the Unity client
gets built against the real protocol before the heavy engines exist, and the
energy VAD in particular is a usable fallback rather than a mock.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import numpy as np

from ..audio import rms
from .base import AudioChunk, VadEvent

_TWO_PI = 2.0 * np.pi


class EnergyVad:
    """Energy-threshold VAD.

    A genuinely usable fallback: it works on real microphone input with a
    sensible ``energy_threshold``, and it is what stub mode uses so the
    interruption path can be exercised without Silero installed.

    Levels are RMS of float32 in ``[-1, 1]``; ordinary speech sits well below
    0.1, so the threshold is a signal level and not a probability.
    """

    name = "energy"

    def __init__(
        self,
        *,
        threshold: float = 0.015,
        min_speech_ms: int = 200,
        min_silence_ms: int = 500,
        max_utterance_ms: int = 15000,
    ) -> None:
        self.threshold = threshold
        self.min_speech_ms = min_speech_ms
        self.min_silence_ms = min_silence_ms
        self.max_utterance_ms = max_utterance_ms
        self.reset()

    def reset(self) -> None:
        self._in_speech = False
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        self._utterance_ms = 0.0

    def push(self, frame: np.ndarray, sample_rate: int) -> VadEvent:
        if frame.size == 0 or sample_rate <= 0:
            return VadEvent.NONE

        frame_ms = frame.size / sample_rate * 1000.0
        voiced = rms(frame) >= self.threshold

        if not self._in_speech:
            if not voiced:
                self._speech_ms = 0.0
                return VadEvent.NONE
            self._speech_ms += frame_ms
            if self._speech_ms < self.min_speech_ms:
                return VadEvent.NONE
            # Confirmed speech onset.
            self._in_speech = True
            self._utterance_ms = self._speech_ms
            self._silence_ms = 0.0
            return VadEvent.SPEECH_START

        self._utterance_ms += frame_ms
        if voiced:
            self._silence_ms = 0.0
        else:
            self._silence_ms += frame_ms

        if self._silence_ms >= self.min_silence_ms or self._utterance_ms >= self.max_utterance_ms:
            self._in_speech = False
            self._speech_ms = 0.0
            self._silence_ms = 0.0
            self._utterance_ms = 0.0
            return VadEvent.SPEECH_END

        return VadEvent.NONE


class StubAsr:
    """Returns canned Chinese phrases so the pipeline can be exercised."""

    name = "stub"

    PHRASES = (
        "你好，能听见我说话吗？",
        "今天天气不错，我们聊点什么吧。",
        "给我讲讲你今天遇到的事情。",
    )

    def __init__(self, delay_s: float = 0.15) -> None:
        self.delay_s = delay_s
        self._next = 0

    async def transcribe(self, samples: np.ndarray, sample_rate: int) -> str:
        await asyncio.sleep(self.delay_s)
        phrase = self.PHRASES[self._next % len(self.PHRASES)]
        self._next += 1
        return phrase


class StubLlm:
    """Streams a canned multi-sentence reply at a realistic pace.

    The default reply deliberately spans several sentences so that sentence
    splitting and per-sentence synthesis are exercised.
    """

    name = "stub"

    DEFAULT_REPLY = "你好呀，我是祀。很高兴在这里见到你。今天想聊点什么呢？"

    def __init__(
        self,
        reply: str = DEFAULT_REPLY,
        *,
        first_token_delay_s: float = 0.10,
        token_delay_s: float = 0.02,
    ) -> None:
        self.reply = reply
        self.first_token_delay_s = first_token_delay_s
        self.token_delay_s = token_delay_s

    async def stream(
        self, messages: list[dict[str, str]], cancel: asyncio.Event
    ) -> AsyncIterator[str]:
        if await _sleep_unless_cancelled(self.first_token_delay_s, cancel):
            return
        for ch in self.reply:
            yield ch
            if await _sleep_unless_cancelled(self.token_delay_s, cancel):
                return


class StubTts:
    """Emits a tone whose envelope tracks the text length.

    The amplitude wobble gives the client's lip sync something to actually
    follow, so the audio path and the mouth can be developed together before real
    synthesis exists.
    """

    name = "stub"

    def __init__(
        self,
        *,
        sample_rate: int = 24000,
        channels: int = 1,
        chunk_ms: int = 20,
        tone_hz: float = 220.0,
        realtime: bool = True,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_ms = chunk_ms
        self.tone_hz = tone_hz
        #: Pace chunks as if streaming. Tests turn this off to run fast.
        self.realtime = realtime
        self._epoch = 0

    def invalidate(self) -> None:
        self._epoch += 1

    async def synthesize(self, text: str, cancel: asyncio.Event) -> AsyncIterator[AudioChunk]:
        epoch = self._epoch

        seconds = float(np.clip(len(text) * 0.12, 0.3, 6.0))
        total = max(1, int(seconds * self.sample_rate))
        t = np.arange(total, dtype=np.float64) / self.sample_rate
        envelope = 0.35 * (0.6 + 0.4 * np.sin(_TWO_PI * 3.0 * t))
        wave = (envelope * np.sin(_TWO_PI * self.tone_hz * t)).astype(np.float32)

        samples_per_chunk = max(1, int(self.sample_rate * self.chunk_ms / 1000))
        for start in range(0, total, samples_per_chunk):
            if cancel.is_set() or epoch != self._epoch:
                return
            block = wave[start : start + samples_per_chunk]
            pcm = (np.clip(block, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
            if self.channels > 1:
                pcm = np.repeat(np.frombuffer(pcm, dtype="<i2"), self.channels).tobytes()
            yield AudioChunk(pcm, self.sample_rate, self.channels)
            if self.realtime:
                await _sleep_unless_cancelled(self.chunk_ms / 1000.0, cancel)


async def _sleep_unless_cancelled(seconds: float, cancel: asyncio.Event) -> bool:
    """Sleep, waking early if cancelled. Returns True when cancelled."""
    if seconds <= 0:
        return cancel.is_set()
    try:
        await asyncio.wait_for(cancel.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        return False
    return True
