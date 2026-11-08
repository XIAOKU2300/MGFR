#!/usr/bin/env python3
"""Small standard-library client for the local SiLLMBridge HTTP service."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from typing import Any

DEFAULT_SERVICE_URL = "http://127.0.0.1:18772"
DEFAULT_EXPRESSION = "auto"
MAX_BODY = 2 * 1024 * 1024


class ClientError(Exception):
    pass


def _http_json(url: str, *, method: str = "GET", payload: Any = None,
               headers: dict[str, str] | None = None, timeout: float = 30) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Accept": "application/json"}
    if data is not None:
        request_headers["Content-Type"] = "application/json; charset=utf-8"
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        host = (urlsplit(url).hostname or "").lower()
        opener = (urllib.request.build_opener(urllib.request.ProxyHandler({}))
                  if host in {"127.0.0.1", "localhost", "::1"} else None)
        response_context = opener.open(req, timeout=timeout) if opener else urllib.request.urlopen(req, timeout=timeout)
        with response_context as response:
            raw = response.read(MAX_BODY + 1)
            if len(raw) > MAX_BODY:
                raise ClientError("HTTP response exceeded the 2 MiB limit")
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ClientError("HTTP response was not valid UTF-8 JSON") from None
    except urllib.error.HTTPError as exc:
        # Never echo an upstream body, headers, or request details: they may contain credentials.
        raise ClientError(f"HTTP request failed with status {exc.code}") from None
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, (TimeoutError,)):
            raise ClientError("HTTP request timed out") from None
        raise ClientError("Could not connect to the configured HTTP service") from None
    except TimeoutError:
        raise ClientError("HTTP request timed out") from None
    except OSError:
        raise ClientError("HTTP request failed") from None


def _local_json(base_url: str, path: str, *, method: str = "GET", payload: Any = None) -> Any:
    return _http_json(base_url.rstrip("/") + path, method=method, payload=payload)


def _extract_content(reply: Any) -> str:
    try:
        content = reply["choices"][0]["message"]["content"]
    except (TypeError, KeyError, IndexError):
        raise ClientError("LLM response did not contain a chat message") from None
    if not isinstance(content, str):
        raise ClientError("LLM response content was not a JSON string")
    return content


def parse_plan(content: str) -> dict[str, Any]:
    """Parse raw model JSON; markdown fences and non-object values are rejected."""
    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        raise ClientError("LLM content was not strict JSON; no local action was sent") from None
    if not isinstance(plan, dict):
        raise ClientError("LLM JSON must be an object; no local action was sent")
    if isinstance(plan.get("version"), bool) or plan.get("version") != 1:
        raise ClientError("LLM JSON version must be 1; no local action was sent")
    if not isinstance(plan.get("text"), str):
        raise ClientError("LLM JSON text must be a string; no local action was sent")
    emotion = plan.get("emotion")
    if not isinstance(emotion, str) or emotion not in {"neutral", "happy", "sad", "angry", "surprised", "shy", "thinking", "affection"}:
        raise ClientError("LLM JSON has an unsupported or missing emotion; no local action was sent")
    intensity = plan.get("emotion_intensity", 0.65)
    if isinstance(intensity, bool) or not isinstance(intensity, (int, float)) or not 0 <= intensity <= 1:
        raise ClientError("LLM JSON emotion_intensity must be between 0 and 1; no local action was sent")
    expression = plan.get("expression", DEFAULT_EXPRESSION)
    if not isinstance(expression, str) or expression not in {"auto", "native"}:
        raise ClientError("LLM JSON expression must be auto or native; no local action was sent")
    actions = plan.get("actions")
    if not isinstance(actions, list) or len(actions) > 3:
        raise ClientError("LLM JSON actions must be a list with at most 3 items; no local action was sent")
    previous_at = -1.0
    for action in actions:
        if not isinstance(action, dict) or not isinstance(action.get("name"), str) or not action["name"]:
            raise ClientError("LLM JSON contains an invalid action; no local action was sent")
        at = action.get("at")
        if isinstance(at, bool) or not isinstance(at, (int, float)) or not 0 <= at <= 60 or at < previous_at:
            raise ClientError("LLM JSON action times must be ascending from 0 to 60 seconds; no local action was sent")
        previous_at = at
    return plan


def _model_messages(context: dict[str, Any], catalog: dict[str, Any], user_text: str,
                    history: list[dict[str, str]]) -> list[dict[str, str]]:
    system_prompt = context.get("system_prompt")
    schema = context.get("json_schema")
    if not isinstance(system_prompt, str) or not isinstance(schema, dict):
        raise ClientError("Local context response is missing system_prompt or json_schema")
    catalog_text = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
    schema_text = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    system = f"{system_prompt}\n\nJSON Schema:\n{schema_text}\n\nAvailable catalog:\n{catalog_text}"
    return [{"role": "system", "content": system}, *history, {"role": "user", "content": user_text}]


def perform_turn(message: str, *, service_url: str = DEFAULT_SERVICE_URL,
                 model_url: str | None = None, model: str | None = None,
                 api_key: str | None = None, response_format: bool = True,
                 dry_run: bool = False, history: list[dict[str, str]] | None = None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not message.strip():
        raise ClientError("Message must not be empty")
    context = _local_json(service_url, "/v1/context")
    catalog = _local_json(service_url, "/v1/catalog")
    if not isinstance(context, dict) or not isinstance(catalog, dict):
        raise ClientError("Local service returned an unexpected context or catalog")
    if not model_url:
        raise ClientError("Set SI_LLM_BASE_URL to an OpenAI-compatible API base URL")
    if not model:
        raise ClientError("Set SI_LLM_MODEL to the model name")
    payload: dict[str, Any] = {
        "model": model,
        "messages": _model_messages(context, catalog, message, history or []),
        "temperature": 0.7,
    }
    if response_format:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    reply = _http_json(model_url.rstrip("/") + "/chat/completions", method="POST", payload=payload, headers=headers)
    plan = parse_plan(_extract_content(reply))
    if dry_run:
        return plan, None
    result = _local_json(service_url, "/v1/perform", method="POST", payload=plan)
    if not isinstance(result, dict):
        raise ClientError("Local perform endpoint returned an unexpected response")
    return plan, result


def demo(service_url: str) -> dict[str, Any]:
    plan = {"version": 1, "text": "你好！很高兴见到你。", "emotion": "happy",
            "emotion_intensity": 0.65, "expression": "auto",
            "actions": [{"name": "wave", "at": 0}]}
    result = _local_json(service_url, "/v1/perform", method="POST", payload=plan)
    if not isinstance(result, dict):
        raise ClientError("Local perform endpoint returned an unexpected response")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send a message to an OpenAI-compatible LLM and perform its local plan.")
    parser.add_argument("--message", help="Text to send to the model")
    parser.add_argument("--demo", action="store_true", help="POST a fixed happy + wave plan; makes no remote model call")
    parser.add_argument("--dry-run", action="store_true", help="Call the LLM and parse its plan, without POSTing /perform")
    parser.add_argument("--no-response-format", action="store_true", help="Omit response_format for providers that reject it")
    args = parser.parse_args(argv)
    service_url = os.environ.get("SI_LLM_SERVICE_URL", DEFAULT_SERVICE_URL)
    try:
        if args.demo:
            if args.message is not None or args.dry_run:
                raise ClientError("--demo cannot be combined with --message or --dry-run")
            print(json.dumps(demo(service_url), ensure_ascii=False, indent=2))
            return 0
        if args.message is None:
            parser.error("--message is required unless --demo is used")
        plan, result = perform_turn(
            args.message,
            service_url=service_url,
            model_url=os.environ.get("SI_LLM_BASE_URL"),
            model=os.environ.get("SI_LLM_MODEL"),
            api_key=os.environ.get("SI_LLM_API_KEY"),
            response_format=not args.no_response_format,
            dry_run=args.dry_run,
        )
        if args.dry_run:
            print(json.dumps({"plan": plan, "dry_run": True}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except ClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
