"""Configuration: a TOML file plus environment overrides.

Secrets are never stored in the repository. ``config.toml`` is gitignored and the
API key is preferably supplied through the environment instead.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

SERVICE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = SERVICE_ROOT / "config.toml"
EXAMPLE_CONFIG_PATH = SERVICE_ROOT / "config.example.toml"

CONFIG_PATH_ENV = "MGFR_CONFIG"


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8765


class AudioConfig(BaseModel):
    mic_sample_rate: int = 16000
    mic_channels: int = 1
    frame_ms: int = 20


class EnginesConfig(BaseModel):
    """Which implementation backs each stage. Switch one at a time."""

    vad: str = "stub"
    asr: str = "stub"
    llm: str = "stub"
    tts: str = "stub"

    def as_dict(self) -> dict[str, str]:
        return {"vad": self.vad, "asr": self.asr, "llm": self.llm, "tts": self.tts}


class VadConfig(BaseModel):
    #: Silero speech probability threshold, 0-1.
    threshold: float = 0.5
    #: RMS level threshold for the energy VAD fallback. Speech sits well below
    #: 0.1 RMS, so this is a signal level, not a probability.
    energy_threshold: float = 0.015
    min_speech_ms: int = 200
    min_silence_ms: int = 500
    max_utterance_ms: int = 15000


class AsrConfig(BaseModel):
    model_dir: str = ""
    num_threads: int = 4
    language: str = "zh"


class LlmConfig(BaseModel):
    base_url: str = "https://api.example.com/v1"
    model: str = "example-model"
    api_key: str = ""
    api_key_env: str = "MGFR_LLM_API_KEY"
    system_prompt_file: str = "prompts/system.zh.txt"
    max_tokens: int = 512
    temperature: float = 0.8
    request_timeout_s: float = 60.0

    def resolve_api_key(self) -> str:
        """Prefer the environment over the file, so keys stay out of config.toml."""
        if self.api_key:
            return self.api_key
        return os.environ.get(self.api_key_env, "")

    def load_system_prompt(self) -> str:
        path = Path(self.system_prompt_file)
        if not path.is_absolute():
            path = SERVICE_ROOT / path
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""


class TtsConfig(BaseModel):
    """The existing GPT-SoVITS api_v2 service, reused read-only (constraint #6)."""

    base_url: str = "http://127.0.0.1:9880"
    ref_audio: str = ""
    prompt_text: str = ""
    prompt_language: str = "zh"
    text_language: str = "zh"
    streaming_mode: bool = True
    #: Empty means "omit the field and accept the server default", which is the
    #: preferred setting — the response then carries a real sample rate we can
    #: read. Setting "raw" returns headerless PCM, and the rate becomes an
    #: assumption rather than an observation (constraint #6).
    media_type: str = ""
    max_concurrent: int = 1
    max_sentence_chars: int = 40
    request_timeout_s: float = 120.0

    #: Only used by the stub engine, and as the declared rate before the first
    #: real response arrives. The real rate is always read from the response.
    fallback_sample_rate: int = 24000


class SessionConfig(BaseModel):
    max_history_turns: int = 20


class Config(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    engines: EnginesConfig = Field(default_factory=EnginesConfig)
    vad: VadConfig = Field(default_factory=VadConfig)
    asr: AsrConfig = Field(default_factory=AsrConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    tts: TtsConfig = Field(default_factory=TtsConfig)
    session: SessionConfig = Field(default_factory=SessionConfig)

    #: Where this configuration was loaded from, for diagnostics.
    source_path: Path | None = None

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> Config:
        """Load configuration, falling back to defaults when no file exists.

        Missing config is not an error: stub mode must run with nothing set up.
        """
        resolved: Path | None
        if path is not None:
            resolved = Path(path)
        else:
            env = os.environ.get(CONFIG_PATH_ENV)
            resolved = Path(env) if env else DEFAULT_CONFIG_PATH

        if not resolved.is_file():
            cfg = cls()
            cfg.source_path = None
            return cfg

        with resolved.open("rb") as fh:
            raw: dict[str, Any] = tomllib.load(fh)

        cfg = cls.model_validate(raw)
        cfg.source_path = resolved
        return cfg
