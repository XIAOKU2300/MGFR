"""Silero VAD through onnxruntime.

Verified on CPU against local Chinese and Japanese speech, on 2026-10-18, by
``tests/test_engines_real.py``. Construction fails loudly when the dependency or
the model file is missing.

The one non-obvious part is :data:`CONTEXT`. Silero v5's ONNX graph takes 576
samples per call, not 512: the last 64 samples of the previous window are
prepended to the current 512. Feeding a bare 512-sample window does not raise —
the model still returns a number — but the number is wrong. Measured on a clip
with peak 0.843, the bare-window call never exceeded a speech probability of
0.16 (mean 0.002), while the context-carrying call reached 1.00 (mean 0.77).
This is why the adapter was unverified for so long: it failed quietly, not
loudly.

``engines.vad = "stub"`` still selects :class:`EnergyVad`, which is a working
fallback rather than a mock.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..config import SERVICE_ROOT, VadConfig
from .base import EngineUnavailable, VadEvent

#: Silero v5 processes 512-sample windows at 16 kHz, plus a context prefix.
WINDOW = 512
MODEL_SAMPLE_RATE = 16000

#: Samples of the previous window that the graph expects to be re-fed with each
#: new one. See the module docstring: omit this and the model returns near-zero
#: probability for real speech instead of failing.
CONTEXT = 64


class SileroVad:
    name = "silero"

    def __init__(self, cfg: VadConfig) -> None:
        self.threshold = cfg.threshold
        self.min_speech_ms = cfg.min_speech_ms
        self.min_silence_ms = cfg.min_silence_ms
        self.max_utterance_ms = cfg.max_utterance_ms

        try:
            import onnxruntime
        except ImportError as exc:
            raise EngineUnavailable(
                "onnxruntime is not installed in this venv; see requirements-engines.txt"
            ) from exc

        model_path = self.model_path()
        if not model_path.is_file():
            raise EngineUnavailable(
                f"Silero VAD model not found at {model_path}; download silero_vad.onnx "
                "into dialogue-service/models/"
            )

        try:
            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self._session = onnxruntime.InferenceSession(
                str(model_path), sess_options=options, providers=["CPUExecutionProvider"]
            )
        except Exception as exc:  # noqa: BLE001 - surfaced as a clear engine error
            raise EngineUnavailable(f"could not load the Silero VAD model: {exc}") from exc

        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros(CONTEXT, dtype=np.float32)
        self._sr = np.array(MODEL_SAMPLE_RATE, dtype=np.int64)
        self._pending = np.empty(0, dtype=np.float32)
        self.reset()

    @staticmethod
    def model_path() -> Path:
        return SERVICE_ROOT / "models" / "silero_vad.onnx"

    def reset(self) -> None:
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros(CONTEXT, dtype=np.float32)
        self._pending = np.empty(0, dtype=np.float32)
        self._in_speech = False
        self._speech_ms = 0.0
        self._silence_ms = 0.0
        self._utterance_ms = 0.0

    def _probability(self, window: np.ndarray) -> float:
        # The graph expects the previous window's tail prepended to this one.
        # Feeding the bare window returns a plausible-looking wrong number.
        fed = np.concatenate([self._context, window]).astype(np.float32)
        out, self._state = self._session.run(
            None,
            {
                "input": fed.reshape(1, -1),
                "state": self._state,
                "sr": self._sr,
            },
        )
        self._context = fed[-CONTEXT:]
        return float(out.reshape(-1)[0])

    def push(self, frame: np.ndarray, sample_rate: int) -> VadEvent:
        if frame.size == 0 or sample_rate <= 0:
            return VadEvent.NONE

        # The pipeline feeds 16 kHz mono; anything else is a configuration error.
        if sample_rate != MODEL_SAMPLE_RATE:
            raise EngineUnavailable(
                f"Silero VAD expects {MODEL_SAMPLE_RATE} Hz but received {sample_rate} Hz"
            )

        self._pending = np.concatenate([self._pending, frame.astype(np.float32)])
        event = VadEvent.NONE

        while self._pending.size >= WINDOW:
            window = self._pending[:WINDOW]
            self._pending = self._pending[WINDOW:]
            frame_ms = WINDOW / MODEL_SAMPLE_RATE * 1000.0
            voiced = self._probability(window) >= self.threshold

            if not self._in_speech:
                if not voiced:
                    self._speech_ms = 0.0
                    continue
                self._speech_ms += frame_ms
                if self._speech_ms < self.min_speech_ms:
                    continue
                self._in_speech = True
                self._utterance_ms = self._speech_ms
                self._silence_ms = 0.0
                event = VadEvent.SPEECH_START
                continue

            self._utterance_ms += frame_ms
            if voiced:
                self._silence_ms = 0.0
            else:
                self._silence_ms += frame_ms

            if (
                self._silence_ms >= self.min_silence_ms
                or self._utterance_ms >= self.max_utterance_ms
            ):
                self._in_speech = False
                self._speech_ms = 0.0
                self._silence_ms = 0.0
                self._utterance_ms = 0.0
                event = VadEvent.SPEECH_END

        return event
