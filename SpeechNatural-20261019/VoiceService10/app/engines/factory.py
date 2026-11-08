"""Engine construction from configuration.

Imports are lazy so that stub mode never touches a heavy dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Config
from .base import AsrEngine, EngineUnavailable, LlmEngine, TtsEngine, VadEngine


@dataclass(slots=True)
class Engines:
    vad: VadEngine
    asr: AsrEngine
    llm: LlmEngine
    tts: TtsEngine

    def names(self) -> dict[str, str]:
        """Engine names for the ``hello.ack`` handshake, so the client can show
        a degraded state instead of guessing."""
        return {
            "vad": getattr(self.vad, "name", type(self.vad).__name__),
            "asr": getattr(self.asr, "name", type(self.asr).__name__),
            "llm": getattr(self.llm, "name", type(self.llm).__name__),
            "tts": getattr(self.tts, "name", type(self.tts).__name__),
        }


def build_vad(cfg: Config) -> VadEngine:
    name = cfg.engines.vad
    if name in ("stub", "energy"):
        from .stub import EnergyVad

        return EnergyVad(
            threshold=cfg.vad.energy_threshold,
            min_speech_ms=cfg.vad.min_speech_ms,
            min_silence_ms=cfg.vad.min_silence_ms,
            max_utterance_ms=cfg.vad.max_utterance_ms,
        )
    if name == "silero":
        from .vad_silero import SileroVad

        return SileroVad(cfg.vad)
    raise EngineUnavailable(f"unknown vad engine {name!r}")


def build_asr(cfg: Config) -> AsrEngine:
    name = cfg.engines.asr
    if name == "stub":
        from .stub import StubAsr

        return StubAsr()
    if name in ("sensevoice", "sherpa"):
        from .asr_sensevoice import SenseVoiceAsr

        return SenseVoiceAsr(cfg.asr)
    raise EngineUnavailable(f"unknown asr engine {name!r}")


def build_llm(cfg: Config) -> LlmEngine:
    name = cfg.engines.llm
    if name == "stub":
        from .stub import StubLlm

        return StubLlm()
    if name in ("openai", "openai-compat"):
        from .llm_openai import OpenAiCompatLlm

        return OpenAiCompatLlm(cfg.llm)
    raise EngineUnavailable(f"unknown llm engine {name!r}")


def build_tts(cfg: Config) -> TtsEngine:
    name = cfg.engines.tts
    if name == "stub":
        from .stub import StubTts

        return StubTts(sample_rate=cfg.tts.fallback_sample_rate)
    if name in ("gptsovits", "gpt-sovits"):
        from .tts_gptsovits import GptSovitsTts

        return GptSovitsTts(cfg.tts)
    raise EngineUnavailable(f"unknown tts engine {name!r}")


def build_all(cfg: Config) -> Engines:
    """Build every engine. Raises :class:`EngineUnavailable` on misconfiguration."""
    engines = Engines(vad=build_vad(cfg), asr=build_asr(cfg), llm=build_llm(cfg), tts=build_tts(cfg))
    if cfg.engines.tts in ("gptsovits", "gpt-sovits") and cfg.engines.asr in ("sensevoice", "sherpa"):
        from .asr_sensevoice import SenseVoiceAsr
        # A separate local recognizer keeps assistant speech verification out of
        # the user's live microphone recognizer and conversation history.
        engines.tts.verifier = SenseVoiceAsr(cfg.asr)
    return engines
