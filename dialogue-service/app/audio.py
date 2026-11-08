"""PCM helpers.

Everything on the wire is S16LE. Internally we work in float32 mono in
``[-1, 1]`` because that is what VAD and ASR libraries expect.
"""

from __future__ import annotations

import numpy as np

_INT16_SCALE = 1.0 / 32768.0


def pcm_s16le_to_float32(payload: bytes, channels: int = 1) -> np.ndarray:
    """Decode S16LE bytes to float32 mono, downmixing if needed."""
    samples = np.frombuffer(payload, dtype="<i2")
    if channels > 1:
        if samples.size % channels:
            # Drop a trailing partial frame rather than raising: a truncated
            # network frame should not kill the session.
            samples = samples[: samples.size - (samples.size % channels)]
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples.astype(np.float32) * _INT16_SCALE


def float32_to_pcm_s16le(samples: np.ndarray) -> bytes:
    """Encode float32 mono in [-1, 1] to S16LE bytes, clipping safely."""
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def rms(samples: np.ndarray) -> float:
    """Root-mean-square level of a float32 buffer."""
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))


def resample_linear(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Crude linear resampling.

    Good enough for VAD and for a fallback path. ASR quality work should use a
    proper resampler; note that the microphone path is already 16 kHz mono, so
    this is normally a no-op.
    """
    if src_rate == dst_rate or samples.size == 0:
        return samples
    duration = samples.size / float(src_rate)
    dst_count = max(1, int(round(duration * dst_rate)))
    src_idx = np.linspace(0.0, samples.size - 1, num=dst_count, dtype=np.float64)
    return np.interp(src_idx, np.arange(samples.size), samples).astype(np.float32)
