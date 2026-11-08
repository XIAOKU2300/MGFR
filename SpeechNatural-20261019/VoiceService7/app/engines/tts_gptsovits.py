"""GPT-SoVITS adapter.

Constraint #6: nothing under ``F:\\GPT-SoVITS`` is modified. The existing 小酒狐
configuration is reused as-is, and streamed audio is parsed according to the
format the server **actually** returns rather than an assumed one.

Constraint #7: ``api_v2.py`` has no request-cancellation endpoint, and closing the
HTTP connection does not stop GPU inference. So synthesis is serialised, sentences
are kept short to bound how long a stale request can block, and output from a
superseded generation epoch is discarded.

The container is stripped here. A partially written WAV is never forwarded to the
client as though it were complete.

**Verified against the live server**, 2026-10-18: the installed ``api_v2.py``
returned real speech at 32000 Hz mono s16le, the Unity client played it back and
lip-synced to it, and the container parsing below was confirmed against what the
server actually sent. It still fails loudly on a format it does not recognise
instead of guessing.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

import httpx

from ..config import TtsConfig
from ..text import normalize_for_speech, prepare_tts_text
from ..speech_pcm import SpeechPcmSmoother
from .base import AudioChunk, EngineUnavailable

logger = logging.getLogger(__name__)


class _ResponseAudioParser:
    """Separates a GPT-SoVITS response body into PCM and reports the real format.

    The endpoint returns either a WAV container or headerless PCM depending on
    ``media_type`` and ``streaming_mode``. We detect which rather than assume, and
    when there is a container we read the true sample rate out of it.
    """

    def __init__(self, fallback_sample_rate: int, fallback_channels: int = 1) -> None:
        self.sample_rate = fallback_sample_rate
        self.channels = fallback_channels
        self.rate_is_observed = False  # True once read from a real container
        self._buf = bytearray()
        self._decided = False
        self._header_consumed = False

    def feed(self, data: bytes) -> bytes:
        """Append bytes; return PCM ready to forward (possibly empty)."""
        if self._header_consumed:
            return data

        self._buf.extend(data)

        if not self._decided:
            if len(self._buf) < 4:
                return b""
            self._decided = True
            if bytes(self._buf[:4]) != b"RIFF":
                # Headerless PCM. Everything buffered is audio, at the configured
                # rate — which is an assumption, not an observation.
                self._header_consumed = True
                out = bytes(self._buf)
                self._buf.clear()
                return out

        return self._consume_wav_header() or b""

    def _consume_wav_header(self) -> bytes | None:
        buf = self._buf
        if len(buf) < 12:
            return None
        if bytes(buf[8:12]) != b"WAVE":
            raise EngineUnavailable(
                "GPT-SoVITS response begins with RIFF but is not WAVE; "
                "refusing to parse the container"
            )

        pos = 12
        seen_fmt = False
        while True:
            if pos + 8 > len(buf):
                return None
            chunk_id = bytes(buf[pos : pos + 4])
            size = int.from_bytes(buf[pos + 4 : pos + 8], "little")
            body = pos + 8

            if chunk_id == b"fmt ":
                if body + size > len(buf):
                    return None
                if size < 16:
                    raise EngineUnavailable("WAV fmt chunk is shorter than 16 bytes")
                audio_format = int.from_bytes(buf[body : body + 2], "little")
                if audio_format != 1:
                    raise EngineUnavailable(
                        f"WAV audio format {audio_format} is not PCM; refusing to guess"
                    )
                bits = int.from_bytes(buf[body + 14 : body + 16], "little")
                if bits != 16:
                    raise EngineUnavailable(
                        f"WAV is {bits}-bit but the wire format is S16LE only"
                    )
                self.channels = int.from_bytes(buf[body + 2 : body + 4], "little") or self.channels
                self.sample_rate = (
                    int.from_bytes(buf[body + 4 : body + 8], "little") or self.sample_rate
                )
                self.rate_is_observed = True
                seen_fmt = True
                pos = body + size + (size & 1)
                continue

            if chunk_id == b"data":
                if not seen_fmt:
                    return None
                end = body + size
                if size == 0 or size >= 0x7fffffff or end >= len(buf):
                    # The data chunk is still arriving. Forward what we have and
                    # treat the header as consumed; later feeds pass straight through.
                    out = bytes(buf[body:])
                    self._buf.clear()
                    self._header_consumed = True
                    return out
                out = bytes(buf[body:end])
                cut = min(len(buf), end + (size & 1))
                del buf[:cut]
                self._header_consumed = True
                return out

            # Unknown chunk (LIST, fact, ...) — skip it.
            if body + size > len(buf):
                return None
            pos = body + size + (size & 1)


class GptSovitsTts:
    name = "gptsovits"

    def __init__(self, cfg: TtsConfig) -> None:
        self.cfg = cfg
        #: GPT-SoVITS has no cancellation endpoint, so requests must not overlap.
        self._sem = asyncio.Semaphore(max(1, cfg.max_concurrent))
        self._epoch = 0
        self._last_sample_rate: int | None = None
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.cfg.request_timeout_s, connect=10.0), trust_env=False, limits=httpx.Limits(max_connections=2, max_keepalive_connections=2, keepalive_expiry=120))
        return self._client

    async def aclose(self):
        if self._client is not None:
            await self._client.aclose()

    def invalidate(self) -> None:
        """Mark in-flight synthesis stale. Its output will be discarded."""
        self._epoch += 1

    @property
    def last_sample_rate(self) -> int | None:
        """Rate observed in the most recent response, or None if never seen."""
        return self._last_sample_rate

    def endpoint(self) -> str:
        return self.cfg.base_url.rstrip("/") + "/tts"

    def payload(self, text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "text": prepare_tts_text(text),
            "text_lang": self.cfg.text_language,
            "ref_audio_path": self.cfg.ref_audio,
            "prompt_lang": self.cfg.prompt_language,
            "streaming_mode": 1 if self.cfg.streaming_mode else 0,
            "text_split_method": "cut0",
            "fragment_interval": .10,
            "speed_factor": 1.0,
            "batch_size": 1,
            "split_bucket": False,
        }
        if self.cfg.prompt_text:
            payload["prompt_text"] = self.cfg.prompt_text
        if self.cfg.media_type:
            # Only set when explicitly configured: omitting it keeps the server
            # default, whose container carries a real sample rate.
            payload["media_type"] = self.cfg.media_type
        return payload

    async def synthesize(self, text: str, cancel: asyncio.Event) -> AsyncIterator[AudioChunk]:
        text = normalize_for_speech(text)
        if not text:
            return
        epoch = self._epoch
        async with self._sem:
            if cancel.is_set() or epoch != self._epoch:
                return
            # The installed server can omit a short first segment when several
            # newline segments share one request. Issue protected phrases in
            # order, under the same cancellation epoch and serialization lock.
            for phrase in prepare_tts_text(text).splitlines():
                if cancel.is_set() or epoch != self._epoch:
                    return
                async for chunk in self._stream(phrase, epoch, cancel):
                    yield chunk

    async def _stream(
        self, text: str, epoch: int, cancel: asyncio.Event
    ) -> AsyncIterator[AudioChunk]:
        timeout = httpx.Timeout(self.cfg.request_timeout_s, connect=10.0)
        chunk_ms = 20
        warned_about_rate = False

        client = self._get_client()
        async with client.stream("POST", self.endpoint(), json=self.payload(text)) as response:
            if response.status_code != 200:
                body = (await response.aread()).decode("utf-8", "replace")
                raise EngineUnavailable(
                    f"GPT-SoVITS returned HTTP {response.status_code}: {body[:300]}"
                )

            parser = _ResponseAudioParser(self.cfg.fallback_sample_rate)
            carry = bytearray()
            smoother = None

            async for data in response.aiter_bytes():
                if cancel.is_set() or epoch != self._epoch:
                    return  # superseded: discard the remainder, forward nothing
                pcm = parser.feed(data)
                if not pcm:
                    continue

                if not parser.rate_is_observed and not warned_about_rate:
                    logger.warning(
                        "GPT-SoVITS returned headerless PCM; assuming %d Hz. "
                        "Verify the real rate against the server "
                        "(docs/constraints.md #6).",
                        parser.sample_rate,
                    )
                    warned_about_rate = True

                self._last_sample_rate = parser.sample_rate
                if smoother is None:
                    smoother = SpeechPcmSmoother(parser.sample_rate, parser.channels)
                carry.extend(smoother.push(pcm))
                frame_bytes = max(
                    2, int(parser.sample_rate * chunk_ms / 1000) * parser.channels * 2
                )
                while len(carry) >= frame_bytes:
                    out = bytes(carry[:frame_bytes])
                    del carry[:frame_bytes]
                    yield AudioChunk(out, parser.sample_rate, parser.channels)

            if (smoother is None or not smoother.voiced) and not cancel.is_set() and epoch == self._epoch:
                raise EngineUnavailable("GPT-SoVITS returned no speech audio")
            if smoother is not None and not cancel.is_set() and epoch == self._epoch:
                carry.extend(smoother.flush())
            while len(carry) >= frame_bytes and not cancel.is_set() and epoch == self._epoch:
                out = bytes(carry[:frame_bytes]); del carry[:frame_bytes]
                yield AudioChunk(out, parser.sample_rate, parser.channels)
            if carry and not cancel.is_set() and epoch == self._epoch:
                yield AudioChunk(bytes(carry), parser.sample_rate, parser.channels)
