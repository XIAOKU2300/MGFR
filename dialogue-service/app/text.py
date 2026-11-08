"""Sentence splitting for short-sentence synthesis.

GPT-SoVITS has no cancellation endpoint, so a stale request keeps the GPU busy
until it finishes (docs/constraints.md #7). Keeping sentences short bounds how
long that can be, which is the whole point of this module.
"""

from __future__ import annotations

#: Hard terminators — a sentence ends here, always.
TERMINATORS = "。！？!?；;\n"

#: Soft breaks — used only when a sentence has grown past the limit.
SOFT_BREAKS = "，,、：: 　"


def split_sentences(text: str, max_chars: int = 40) -> list[str]:
    """Split a complete string into synthesis-sized sentences."""
    acc = SentenceAccumulator(max_chars=max_chars)
    out = list(acc.push(text))
    out.extend(acc.flush())
    return out


class SentenceAccumulator:
    """Incremental sentence splitting for a streaming LLM response.

    Feed it deltas as they arrive; it returns the sentences that are now complete.
    Call :meth:`flush` when the stream ends to get the trailing remainder.
    """

    def __init__(self, max_chars: int = 40) -> None:
        if max_chars < 1:
            raise ValueError("max_chars must be >= 1")
        self.max_chars = max_chars
        self._buf = ""

    def push(self, delta: str) -> list[str]:
        """Append a delta and return any sentences completed by it."""
        self._buf += delta
        ready: list[str] = []
        while True:
            sentence = self._take_one()
            if sentence is None:
                break
            ready.append(sentence)
        return ready

    def flush(self) -> list[str]:
        """Return whatever is left, and reset."""
        remainder = self._buf.strip()
        self._buf = ""
        return [remainder] if remainder else []

    @property
    def pending(self) -> str:
        return self._buf

    def _take_one(self) -> str | None:
        while True:
            sentence = self._split_once()
            if sentence is None:
                return None
            if _has_content(sentence):
                return sentence
            # A run of punctuation carries nothing to synthesise. Dropping it here
            # saves a pointless round trip to GPT-SoVITS for a silent sentence.

    def _split_once(self) -> str | None:
        # Prefer the earliest hard terminator.
        hard = -1
        for i, ch in enumerate(self._buf):
            if ch in TERMINATORS:
                hard = i
                break

        if hard != -1:
            sentence = self._buf[: hard + 1].strip()
            self._buf = self._buf[hard + 1 :]
            return sentence or None

        # Otherwise force a break if we have run long enough.
        if len(self._buf) >= self.max_chars:
            cut = -1
            for i in range(min(self.max_chars, len(self._buf)) - 1, -1, -1):
                if self._buf[i] in SOFT_BREAKS:
                    cut = i
                    break
            if cut <= 0:
                cut = self.max_chars - 1
            sentence = self._buf[: cut + 1].strip()
            self._buf = self._buf[cut + 1 :]
            return sentence or None

        return None


def _has_content(sentence: str) -> bool:
    """True when the sentence has something in it besides punctuation."""
    return bool(sentence.strip().strip(TERMINATORS).strip())
