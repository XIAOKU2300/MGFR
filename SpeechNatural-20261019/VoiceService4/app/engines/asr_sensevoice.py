"""SenseVoice ASR through sherpa-onnx, running on CPU.

Verified on CPU against local audio, 2026-10-18, by
``tests/test_engines_real.py``: the model's own ``zh.wav`` transcribed to Chinese
and the 小酒狐 reference clip to Japanese. Construction still fails loudly with
:class:`EngineUnavailable` rather than degrading silently, so a misconfiguration
shows up as an explicit error on the client.

Reference: https://k2-fsa.github.io/sherpa/onnx/sense-voice/index.html
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from ..audio import resample_linear
from ..config import AsrConfig
from .base import EngineUnavailable

#: SenseVoice models are trained at 16 kHz.
MODEL_SAMPLE_RATE = 16000


class SenseVoiceAsr:
    name = "sensevoice"

    def __init__(self, cfg: AsrConfig) -> None:
        self.cfg = cfg
        if not cfg.model_dir:
            raise EngineUnavailable(
                "asr.model_dir is empty; point it at the sherpa-onnx SenseVoice model"
            )
        model_dir = Path(cfg.model_dir)
        if not model_dir.is_dir():
            raise EngineUnavailable(f"asr.model_dir does not exist: {model_dir}")

        try:
            import sherpa_onnx
        except ImportError as exc:
            raise EngineUnavailable(
                "sherpa-onnx is not installed in this venv; see requirements-engines.txt"
            ) from exc

        self._recognizer = self._build(sherpa_onnx, model_dir)

    def _build(self, sherpa_onnx, model_dir: Path):
        model = model_dir / "model.int8.onnx"
        tokens = model_dir / "tokens.txt"
        missing = [p.name for p in (model, tokens) if not p.is_file()]
        if missing:
            raise EngineUnavailable(
                f"{', '.join(missing)} not found under {model_dir}; expected the "
                "INT8 SenseVoice model and its tokens file"
            )
        try:
            # TODO(verify): confirm the constructor signature for the installed
            # sherpa-onnx version before relying on these keyword names.
            return sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(model),
                tokens=str(tokens),
                num_threads=self.cfg.num_threads,
                language=self.cfg.language,
                use_itn=True,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a clear engine error
            raise EngineUnavailable(f"could not build the SenseVoice recognizer: {exc}") from exc

    async def transcribe(self, samples: np.ndarray, sample_rate: int) -> str:
        if sample_rate != MODEL_SAMPLE_RATE:
            samples = resample_linear(samples, sample_rate, MODEL_SAMPLE_RATE)
        # Inference is CPU-bound; keep it off the event loop.
        return await asyncio.to_thread(self._transcribe_sync, samples)

    def _transcribe_sync(self, samples: np.ndarray) -> str:
        stream = self._recognizer.create_stream()
        stream.accept_waveform(MODEL_SAMPLE_RATE, samples)
        self._recognizer.decode_stream(stream)
        return (stream.result.text or "").strip()
