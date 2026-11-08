"""Bound model-generated quiet gaps without changing voiced PCM or speed."""
from __future__ import annotations
import numpy as np


class SpeechPcmSmoother:
    def __init__(self, sample_rate: int, channels: int):
        self.rate = sample_rate
        self.channels = channels
        self.block = max(1, sample_rate // 50) * channels * 2
        self.alignment = channels * 2
        self.buffer = bytearray()
        self.quiet = bytearray()
        self.voiced = False
        self.dropped_bytes = 0
        self.max_gap = int(sample_rate * .32) * self.alignment
        self.leading = int(sample_rate * .04) * self.alignment
        self.trailing = int(sample_rate * .10) * self.alignment

    def push(self, pcm: bytes) -> bytes:
        self.buffer.extend(pcm)
        out = bytearray()
        while len(self.buffer) >= self.block:
            frame = bytes(self.buffer[:self.block]); del self.buffer[:self.block]
            out.extend(self._frame(frame))
        return bytes(out)

    def _frame(self, pcm: bytes) -> bytes:
        samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768
        active = len(samples) and (float(np.max(np.abs(samples))) >= .006 or float(np.sqrt(np.mean(samples*samples))) >= .001)
        if active:
            gap = self._release_quiet(self.max_gap if self.voiced else self.leading)
            self.voiced = True
            return gap + pcm
        self.quiet.extend(pcm)
        if len(self.quiet) > self.max_gap:
            # Preserve both edges of a gap, including quiet consonant onsets.
            half = (self.max_gap // (2*self.alignment))*self.alignment
            old = len(self.quiet)
            self.quiet = self.quiet[:half] + self.quiet[-(self.max_gap-half):]
            self.dropped_bytes += old-len(self.quiet)
        return b''

    def _release_quiet(self, limit: int) -> bytes:
        gap = bytes(self.quiet)
        self.quiet.clear()
        if len(gap) > limit:
            self.dropped_bytes += len(gap)-limit
            gap = gap[-limit:] if limit else b''
        return gap

    def flush(self) -> bytes:
        out = bytearray()
        count = len(self.buffer) - len(self.buffer) % self.alignment
        if count:
            out.extend(self._frame(bytes(self.buffer[:count])))
        self.buffer.clear()
        out.extend(self._release_quiet(self.trailing if self.voiced else 0))
        return bytes(out)
