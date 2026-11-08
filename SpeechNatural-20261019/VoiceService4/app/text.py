"""Spoken text and phrase boundaries, independent from displayed LLM text."""
from __future__ import annotations
import html
import re
import unicodedata

TERMINATORS = "。！？!?\n"
SOFT_BREAKS = "，,、：:；; 　"
_CLOSERS = '”’」』】）)]"\'`*'
_STAGE = r"(?:轻笑|微笑|笑了笑|叹气|轻叹|清嗓|轻咳|咳嗽|眨眼|摇头|点头|歪头|脸红|深吸一口气|停顿|沉默)"


def has_content(text: str) -> bool:
    return any(unicodedata.category(ch)[0] in "LN" for ch in text)


def normalize_for_speech(text: str) -> str:
    """Keep spoken meaning; turn decorative punctuation into normal prosody.

    Numbers remain numbers for the installed Chinese text front end. Limited
    unit/time rules avoid ambiguous raw symbols without guessing pronunciations.
    """
    text = unicodedata.normalize("NFKC", html.unescape(text))
    text = re.sub(r"<think\b[^>]*>.*?(?:</think>|$)", "", text, flags=re.S | re.I)
    text = re.sub(r"```.*?(?:```|$)", "", text, flags=re.S)
    text = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://[^\s，。！？<>]+", "链接", text)
    text = re.sub(r"<br\s*/?>", "。", text, flags=re.I)
    text = re.sub(r"</?[A-Za-z][^>]*>", "", text)
    text = re.sub(r"[（(]\s*" + _STAGE + r"\s*[)）]", "", text)
    text = re.sub(r"\*{1,2}\s*" + _STAGE + r"\s*\*{1,2}", "", text)
    text = re.sub(r"(?m)^\s*(?:#{1,6}\s*|[-+*]\s+|\d+[.)、]\s+)", "", text)
    text = re.sub(r"^\s*(?:祀|小葱|助手|assistant)\s*[:：]\s*", "", text, flags=re.I)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = text.replace("*", "").replace("_", " ")
    text = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]", "", text)
    text = re.sub(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?![\d:])",
                  lambda m: str(int(m[1])) + "点" + (str(int(m[2])) + "分" if int(m[2]) else "整"), text)
    text = re.sub(r"(?<![\d.])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d.])", lambda m: m[0].replace(",", ""), text)
    text = re.sub(r"([-+]?\d+(?:\.\d+)?)\s*%", lambda m: "百分之" + m[1].replace("-", "负").lstrip("+"), text)
    units = {"mm": "毫米", "cm": "厘米", "km": "公里", "kg": "千克", "ml": "毫升", "°c": "摄氏度"}
    text = re.sub(r"(\d(?:\.\d+)?)\s*(mm|cm|km|kg|ml|°c)(?![A-Za-z])",
                  lambda m: m[1] + units[m[2].lower()], text, flags=re.I)
    text = re.sub(r"…+|⋯+|\.{2,}", "，", text)
    text = re.sub(r"[—–]+|--+|[~～]+", "，", text)
    text = re.sub(r"[!?！？]+", lambda m: "？" if "?" in m[0] or "？" in m[0] else "！", text)
    text = text.translate(str.maketrans({",": "，", ";": "。", "；": "。", ":": "，", "：": "，",
                                       "“": "", "”": "", "「": "", "」": "", "『": "", "』": "", '"': "",
                                       "(": "", ")": "", "（": "", "）": "", "[": "", "]": "", "【": "", "】": ""}))
    text = re.sub(r"\n\s*\n", "。", text)
    text = text.replace("\n", "，").replace("\r", "")
    text = re.sub(r"[，、]+", "，", text)
    text = re.sub(r"[，、]+([。！？])", r"\1", text)
    text = re.sub(r"。+", "。", text)
    text = re.sub(r"([。！？])，+", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    text = text.lstrip("，。！？!?;；:：、…—~ ").rstrip("，、 ")
    if not has_content(text):
        return ""
    if text[-1] not in "。！？.!?":
        text = text.rstrip("，、 ") + "。"
    return text


def split_sentences(text: str, max_chars: int = 64) -> list[str]:
    acc = SentenceAccumulator(max_chars=max_chars)
    return acc.push(text) + acc.flush()


class SentenceAccumulator:
    """Keep short replies and comma clauses together; wait for closing marks.

    One token of lookahead keeps repeated punctuation and closing quotes on the
    same phrase. Decimal points, version numbers and Latin words are not cut.
    """
    def __init__(self, max_chars: int = 64, min_chars: int = 12):
        if max_chars < 8:
            raise ValueError("speech phrase limit must be at least 8")
        self.max_chars = max_chars
        self.min_chars = min(min_chars, max_chars)
        self._buf = ""

    @property
    def pending(self) -> str:
        return self._buf

    def push(self, delta: str) -> list[str]:
        self._buf += delta
        return self._drain(False)

    def flush(self) -> list[str]:
        return self._drain(True)

    def _drain(self, final: bool) -> list[str]:
        result = []
        while self._buf:
            cut = self._boundary(final)
            if cut is None:
                break
            raw, self._buf = self._buf[:cut], self._buf[cut:]
            spoken = normalize_for_speech(raw)
            if spoken:
                result.append(spoken)
        return result

    def _boundary(self, final: bool) -> int | None:
        text = self._buf
        # Do not speak fragments of a reasoning or fenced-code block.
        if not final and (("<think" in text.lower() and "</think>" not in text.lower()) or text.count("```") % 2):
            return None
        length = len(text)
        for i, char in enumerate(text[:self.max_chars]):
            hard = char in TERMINATORS
            if char == ".":
                if i + 1 == length and not final:
                    return None
                hard = not ((i > 0 and text[i-1].isdigit() and i+1 < length and text[i+1].isdigit()) or
                            (i > 0 and text[i-1] == ".") or (i+1 < length and text[i+1] == "."))
                if i > 0 and i+1 < length and text[i-1].isascii() and text[i-1].isalnum() and text[i+1].isalnum():
                    hard = False
            if not hard:
                continue
            end = i + 1
            while end < length and (text[end] in TERMINATORS or text[end] in _CLOSERS):
                end += 1
            if end == length and not final:
                return None
            content = sum(unicodedata.category(c)[0] in "LN" for c in normalize_for_speech(text[:end]))
            if content >= self.min_chars:
                return end
        if length >= self.max_chars:
            soft = [i+1 for i, char in enumerate(text[:self.max_chars]) if char in SOFT_BREAKS and i >= self.min_chars]
            if soft:
                return soft[-1]
            if not final and length < self.max_chars + 32:
                return None
            cut = min(self.max_chars, length)
            # Keep an ASCII word, decimal or version token intact at the cap.
            while cut < length and text[cut-1].isascii() and text[cut-1].isalnum() and (text[cut].isalnum() or text[cut] in ".-_"):
                cut += 1
            return cut
        return length if final else None


def prepare_tts_text(text: str) -> str:
    # The installed voice can swallow a short leading clause if several complete
    # sentences share one semantic decode. Preserve those strong boundaries,
    # while commas/colons/hesitation marks stay inside a single sentence.
    return re.sub(r"([。！？])(?=[^。！？])", r"\1\n", normalize_for_speech(text))
