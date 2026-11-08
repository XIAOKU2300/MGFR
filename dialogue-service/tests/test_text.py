"""Sentence-splitting tests.

Short sentences are what bound how long a stale GPT-SoVITS request can block
(constraint #7), so this splitting behaviour is load-bearing, not cosmetic.
"""

from __future__ import annotations

import pytest

from app.text import SentenceAccumulator, split_sentences


def test_splits_on_hard_terminators() -> None:
    assert split_sentences("你好。今天很好！走吗？") == ["你好。", "今天很好！", "走吗？"]


def test_streaming_matches_batch() -> None:
    text = "你好呀，我是祀。很高兴见到你。今天想聊点什么呢？"
    streamed: list[str] = []
    acc = SentenceAccumulator(max_chars=40)
    for ch in text:
        streamed.extend(acc.push(ch))
    streamed.extend(acc.flush())
    assert streamed == split_sentences(text)


def test_forces_a_break_at_a_soft_break_past_the_limit() -> None:
    acc = SentenceAccumulator(max_chars=10)
    ready = acc.push("一二三四五六，七八九十十一十二")
    assert ready, "a sentence past the limit must be released without waiting for a terminator"
    assert len(ready[0]) <= 10


def test_forces_a_hard_cut_when_there_is_no_soft_break() -> None:
    acc = SentenceAccumulator(max_chars=8)
    ready = acc.push("一二三四五六七八九十")
    assert ready
    assert len(ready[0]) <= 8


def test_flush_returns_the_remainder_once() -> None:
    acc = SentenceAccumulator(max_chars=40)
    assert acc.push("没有标点") == []
    assert acc.flush() == ["没有标点"]
    assert acc.flush() == []
    assert acc.pending == ""


def test_whitespace_only_input_produces_nothing() -> None:
    acc = SentenceAccumulator(max_chars=40)
    assert acc.push("   \n  ") == []
    assert acc.flush() == []


def test_empty_delta_is_harmless() -> None:
    acc = SentenceAccumulator(max_chars=40)
    assert acc.push("") == []


def test_max_chars_must_be_positive() -> None:
    with pytest.raises(ValueError):
        SentenceAccumulator(max_chars=0)


def test_a_run_of_punctuation_is_not_synthesised() -> None:
    """Synthesising a lone terminator would be a wasted GPU round trip."""
    assert split_sentences("你好。。") == ["你好。"]
    assert split_sentences("。。") == []
    assert split_sentences("你好。！？") == ["你好。"]
