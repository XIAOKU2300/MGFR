"""Real SenseVoice and Silero runs, against local audio on the CPU.

These are integration tests, not unit tests. They are **skipped, not failed**,
when the engine packages or the model files are absent, so the ordinary test run
stays fast and dependency-free and a fresh clone is not red for a reason that has
nothing to do with the code.

Both adapters were written against their documented APIs and were, until this
file existed, marked unverified. This is what unmarks them.

The three levels are kept apart on purpose, because collapsing them is how a
project ends up claiming a voice conversation it never had:

1. **audio received** — a local file decodes to N samples at a known rate.
   Passing this proves nothing about recognition.
2. **recognition succeeded** — a transcript came back. Passing this proves the
   ASR works; it does not prove a conversation works.
3. **full voice conversation succeeded** — microphone to reply, end to end.
   **Not reachable here and not claimed.** It needs a real LLM, and this project
   has no LLM address, model or key of its own, so the LLM is a stub. Typed text
   reaching real GPT-SoVITS is real speech, but it is not this.

Run them with output:

    .venv\\Scripts\\python.exe -I -m pytest tests/test_engines_real.py -q -s
"""

from __future__ import annotations

import os
import wave
from pathlib import Path

import numpy as np
import pytest

from app.audio import pcm_s16le_to_float32, resample_linear, rms
from app.config import SERVICE_ROOT, AsrConfig, VadConfig
from app.engines.asr_sensevoice import MODEL_SAMPLE_RATE, SenseVoiceAsr
from app.engines.base import EngineUnavailable, VadEvent
from app.engines.vad_silero import WINDOW, SileroVad

MODELS = SERVICE_ROOT / "models"

#: The reference clip the service actually uses for GPT-SoVITS. Local, never
#: committed. Overridable so this file does not hard-code one machine's layout.
REFERENCE_CLIP = Path(
    os.environ.get(
        "MGFR_TEST_AUDIO",
        r"F:\GPT-SoVITS\GPT-SoVITS-v2pro-20250604-nvidia50"
        r"\GPT-SoVITS-v2pro-20250604-nvidia50\ref_xiaojiuhu.wav",
    )
)


def _sensevoice_dir() -> Path | None:
    """The extracted SenseVoice model directory, wherever the tarball put it."""
    if not MODELS.is_dir():
        return None
    for candidate in sorted(MODELS.iterdir()):
        if candidate.is_dir() and (candidate / "model.int8.onnx").is_file():
            return candidate
    return None


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Decode a 16-bit PCM WAV to float32 mono, at its own sample rate.

    Uses the standard library rather than soundfile on purpose: the engines need
    only numpy, and adding an audio dependency for the sake of a test would put
    it in the service's install path too.
    """
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    assert width == 2, f"expected 16-bit PCM, got {width * 8}-bit"
    return pcm_s16le_to_float32(frames, channels), rate


def _local_speech() -> Path:
    """The model's own Chinese test clip: local audio, and Chinese, which is the
    language this project speaks."""
    model_dir = _sensevoice_dir()
    if model_dir is not None:
        clip = model_dir / "test_wavs" / "zh.wav"
        if clip.is_file():
            return clip
    if REFERENCE_CLIP.is_file():
        return REFERENCE_CLIP
    pytest.skip("no local speech available to test with")


def _build_vad() -> SileroVad:
    try:
        return SileroVad(VadConfig())
    except EngineUnavailable as exc:
        pytest.skip(f"Silero VAD unavailable: {exc}")


def _build_asr(language: str = "zh") -> SenseVoiceAsr:
    model_dir = _sensevoice_dir()
    if model_dir is None:
        pytest.skip("no SenseVoice model under dialogue-service/models/")
    try:
        return SenseVoiceAsr(AsrConfig(model_dir=str(model_dir), language=language))
    except EngineUnavailable as exc:
        pytest.skip(f"SenseVoice unavailable: {exc}")


# --- level 1: audio received --------------------------------------------------


def test_local_audio_decodes() -> None:
    """Level 1. A file on this machine is real speech, not silence."""
    clip = _local_speech()
    samples, rate = _read_wav(clip)

    assert samples.size > rate, "expected more than a second of audio"
    assert rms(samples) > 0.001, "the clip is silent, so nothing below can pass"

    print(f"\nlevel 1  audio received : {clip.name}, {samples.size} samples at {rate} Hz")
    print(f"         duration        : {samples.size / rate:.2f} s, RMS {rms(samples):.4f}")


# --- level 2: recognition succeeded -------------------------------------------


def test_silero_vad_finds_speech_in_local_audio() -> None:
    """The VAD reports speech, and then reports it ending.

    Both halves matter: a VAD that only ever says SPEECH_START would never close
    an utterance, so nothing would ever be transcribed. The clip ends while the
    speaker is still talking, so a second of silence is appended to give the
    end-of-speech path something to close on.
    """
    vad = _build_vad()
    samples, rate = _read_wav(_local_speech())
    if rate != MODEL_SAMPLE_RATE:
        samples = resample_linear(samples, rate, MODEL_SAMPLE_RATE)
    samples = np.concatenate([samples, np.zeros(MODEL_SAMPLE_RATE, dtype=np.float32)])

    events: list[tuple[float, VadEvent]] = []
    for start in range(0, samples.size - WINDOW + 1, WINDOW):
        event = vad.push(samples[start : start + WINDOW], MODEL_SAMPLE_RATE)
        if event is not VadEvent.NONE:
            events.append((start / MODEL_SAMPLE_RATE, event))

    kinds = [event for _, event in events]
    assert VadEvent.SPEECH_START in kinds, f"no speech onset; events were {kinds}"
    assert VadEvent.SPEECH_END in kinds, (
        f"speech never closed, so no utterance would be transcribed; events were {kinds}"
    )
    assert kinds.index(VadEvent.SPEECH_START) < kinds.index(VadEvent.SPEECH_END), (
        f"speech ended before it started; events were {kinds}"
    )

    print(f"\nSilero VAD : {len(events)} transitions over {samples.size / MODEL_SAMPLE_RATE:.2f} s")
    for seconds, event in events:
        print(f"             {seconds:6.2f} s  {event.name}")


async def test_sensevoice_transcribes_local_audio() -> None:
    """The ASR returns text for a clip that is known to contain speech."""
    asr = _build_asr(language="zh")
    clip = _local_speech()
    samples, rate = _read_wav(clip)

    text = await asr.transcribe(samples, rate)

    print(f"\nSenseVoice : {clip.name} -> {text!r}")
    print(f"             {samples.size} samples at {rate} Hz, engine {asr.name}")

    assert text.strip() != "", "recognition returned nothing for audible speech"
    assert any("\u4e00" <= ch <= "\u9fff" for ch in text), (
        f"expected Chinese characters from a Chinese clip, got {text!r}"
    )


async def test_sensevoice_handles_a_second_language() -> None:
    """The same engine, told the audio is Japanese, still returns text.

    The reference voice is Japanese, so this is the language the real path would
    actually be asked for. It is a smoke check, not a quality measurement.
    """
    if not REFERENCE_CLIP.is_file():
        pytest.skip(f"reference clip not present at {REFERENCE_CLIP}")

    asr = _build_asr(language="ja")
    samples, rate = _read_wav(REFERENCE_CLIP)
    text = await asr.transcribe(samples, rate)

    print(f"\nSenseVoice : reference clip -> {text!r}")
    assert text.strip() != ""


# --- level 3 ------------------------------------------------------------------


def test_a_full_voice_conversation_is_not_claimed() -> None:
    """Level 3 is deliberately unreachable, and this test is the record of that.

    It passes when the LLM really is a stub. If someone later configures a real
    LLM, this fails, and that is the point: the claim in the docs has to be
    updated by hand rather than drifting out of date on its own.
    """
    from app.config import Config

    config = Config()
    assert config.engines.llm == "stub", (
        "a real LLM is configured now; update docs/architecture.md and this file "
        "to stop calling the text path simulated"
    )
