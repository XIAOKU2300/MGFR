"""GPT-SoVITS response-parsing tests.

This parser is the part of the adapter most likely to be wrong, and the part the
architecture document calls out explicitly: read the format from the response, and
never forward a partially written container as if it were complete
(docs/constraints.md #6).
"""

from __future__ import annotations

import struct

import pytest

from app.engines.base import EngineUnavailable
from app.engines.tts_gptsovits import _ResponseAudioParser

PCM = bytes(range(0, 200))  # 100 int16 samples


def make_wav(
    pcm: bytes, rate: int, *, channels: int = 1, bits: int = 16, audio_format: int = 1
) -> bytes:
    block_align = channels * bits // 8
    fmt = struct.pack(
        "<HHIIHH", audio_format, channels, rate, rate * block_align, block_align, bits
    )
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    chunks += b"data" + struct.pack("<I", len(pcm)) + pcm
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks


def test_a_complete_wav_is_stripped_to_pcm() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    out = parser.feed(make_wav(PCM, 32000))
    assert out == PCM
    assert parser.sample_rate == 32000
    assert parser.rate_is_observed


def test_the_real_sample_rate_wins_over_the_fallback() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    parser.feed(make_wav(PCM, 44100))
    assert parser.sample_rate == 44100


def test_a_wav_arriving_one_byte_at_a_time_is_reassembled() -> None:
    wav = make_wav(PCM, 32000)
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    out = b"".join(parser.feed(wav[i : i + 1]) for i in range(len(wav)))
    assert out == PCM
    assert parser.sample_rate == 32000
    assert parser.rate_is_observed


def test_a_wav_arriving_in_awkward_chunks_is_reassembled() -> None:
    wav = make_wav(PCM, 32000)
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    out = b""
    for start in range(0, len(wav), 7):
        out += parser.feed(wav[start : start + 7])
    assert out == PCM


def test_headerless_pcm_passes_through_and_is_flagged_as_unobserved() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    out = parser.feed(PCM)
    assert out == PCM
    assert parser.sample_rate == 24000
    assert not parser.rate_is_observed


def test_headerless_pcm_streamed_in_chunks_passes_through_unchanged() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    out = b"".join(parser.feed(PCM[i : i + 13]) for i in range(0, len(PCM), 13))
    assert out == PCM


def test_stereo_wav_reports_its_channel_count() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    parser.feed(make_wav(PCM, 32000, channels=2))
    assert parser.channels == 2


def test_unknown_chunks_are_skipped() -> None:
    wav = make_wav(PCM, 32000)
    extra = b"LIST" + struct.pack("<I", 4) + b"INFO"
    spliced = wav[:12] + extra + wav[12:]
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    assert parser.feed(spliced) == PCM


def test_a_non_pcm_format_is_refused() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    with pytest.raises(EngineUnavailable):
        parser.feed(make_wav(PCM, 32000, audio_format=3))  # IEEE float


def test_a_non_16_bit_wav_is_refused() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    with pytest.raises(EngineUnavailable):
        parser.feed(make_wav(PCM, 32000, bits=8))


def test_a_riff_that_is_not_wave_is_refused() -> None:
    parser = _ResponseAudioParser(fallback_sample_rate=24000)
    with pytest.raises(EngineUnavailable):
        parser.feed(b"RIFF" + struct.pack("<I", 4) + b"AVI " + b"\x00" * 16)
