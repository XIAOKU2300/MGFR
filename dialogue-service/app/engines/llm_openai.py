"""OpenAI-compatible streaming LLM client.

Cancellation note: closing the HTTP stream stops *us* reading. It does not
guarantee the provider stops generating. That is a billing concern rather than a
correctness one — the round id is what makes late tokens harmless
(docs/constraints.md #7).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import httpx

from ..config import LlmConfig
from .base import EngineUnavailable


def _content_deltas(obj: dict[str, Any]) -> list[str]:
    """Pull text out of one SSE payload, tolerating the usual gateway variations."""
    out: list[str] = []
    for choice in obj.get("choices") or ():
        if not isinstance(choice, dict):
            continue
        delta = choice.get("delta") or choice.get("message") or {}
        if not isinstance(delta, dict):
            continue
        content = delta.get("content")
        if isinstance(content, str) and content:
            out.append(content)
            continue
        # Some gateways use "text" instead of "content".
        text = delta.get("text")
        if isinstance(text, str) and text:
            out.append(text)
    return out


class OpenAiCompatLlm:
    name = "openai"

    def __init__(self, cfg: LlmConfig) -> None:
        self.cfg = cfg
        self.system_prompt = cfg.load_system_prompt()

    def endpoint(self) -> str:
        return self.cfg.base_url.rstrip("/") + "/chat/completions"

    def build_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        if self.system_prompt:
            return [{"role": "system", "content": self.system_prompt}, *messages]
        return list(messages)

    async def stream(
        self, messages: list[dict[str, str]], cancel: asyncio.Event
    ) -> AsyncIterator[str]:
        api_key = self.cfg.resolve_api_key()
        if not api_key:
            raise EngineUnavailable(
                "the LLM API key is empty; set llm.api_key in config.toml or the "
                f"{self.cfg.api_key_env} environment variable"
            )

        payload = {
            "model": self.cfg.model,
            "messages": self.build_messages(messages),
            "stream": True,
            "max_tokens": self.cfg.max_tokens,
            "temperature": self.cfg.temperature,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        timeout = httpx.Timeout(self.cfg.request_timeout_s, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", self.endpoint(), json=payload, headers=headers
            ) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode("utf-8", "replace")
                    raise EngineUnavailable(
                        f"LLM returned HTTP {response.status_code}: {body[:300]}"
                    )
                async for line in response.aiter_lines():
                    if cancel.is_set():
                        return
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        return
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(obj, dict):
                        continue
                    for piece in _content_deltas(obj):
                        yield piece
