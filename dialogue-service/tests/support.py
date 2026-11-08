"""Shared test helpers.

Kept out of ``conftest.py`` so tests can import it explicitly rather than relying
on pytest's implicit conftest handling.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from app.engines.factory import Engines
from app.engines.stub import EnergyVad, StubAsr, StubLlm, StubTts
from app.session import Session


def make_engines(
    *,
    vad=None,
    asr=None,
    llm=None,
    tts=None,
) -> Engines:
    """Engines wired entirely from stubs: no models, no network, no GPU."""
    return Engines(
        vad=vad if vad is not None else EnergyVad(),
        asr=asr if asr is not None else StubAsr(delay_s=0.0),
        llm=llm if llm is not None else StubLlm(token_delay_s=0.0),
        tts=tts if tts is not None else StubTts(realtime=False),
    )


def make_session(config, engines=None) -> Session:
    return Session(
        engines=engines if engines is not None else make_engines(),
        config=config,
        out=asyncio.Queue(),
    )


def drain(queue: asyncio.Queue) -> list:
    """Remove and return everything currently queued."""
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    return items


def control_types(items: list) -> list[str]:
    """Message types of the JSON items in ``items``, in order."""
    import json

    return [json.loads(i)["type"] for i in items if isinstance(i, str)]


async def wait_until(predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
    """Poll ``predicate`` until it is true or ``timeout`` elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.01)
    return False
