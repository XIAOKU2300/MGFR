"""Pluggable engines for the VAD → ASR → LLM → TTS pipeline.

Heavy dependencies are imported lazily inside each engine module so that stub
mode runs with the core requirements only.
"""

from .base import (
    AudioChunk,
    AsrEngine,
    EngineUnavailable,
    LlmEngine,
    TtsEngine,
    VadEngine,
    VadEvent,
)

__all__ = [
    "AudioChunk",
    "AsrEngine",
    "EngineUnavailable",
    "LlmEngine",
    "TtsEngine",
    "VadEngine",
    "VadEvent",
]
