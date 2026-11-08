"""Loopback-only memory API. No private config, API key, or transcript logging."""
import contextlib
import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import REVISION
from .runtime import Runtime


class Query(BaseModel):
    text: str = Field(min_length=1, max_length=1800)
    user_id: str = Field(default='owner', pattern=r'^[\w-]{1,64}$')
    character_id: str = Field(default='si', pattern=r'^[\w-]{1,64}$')


class Turn(Query):
    event_id: str = Field(pattern=r'^[\w-]{1,128}$')


def create_app(data=None, knowledge=None):
    root = Path(__file__).resolve().parents[2]
    runtime = Runtime(Path(data or os.environ['MGFR_MEMORY_DATA']), Path(knowledge or root / 'knowledge.zh.json'))

    @contextlib.asynccontextmanager
    async def lifespan(app):
        try:
            await runtime.start()
            yield
        finally:
            await runtime.close()

    app = FastAPI(title='MGFR local Mem0', lifespan=lifespan)
    app.state.memory = runtime

    def authorize(key):
        if not key or not hmac.compare_digest(key, os.environ['MGFR_MEMORY_TOKEN']):
            raise HTTPException(401, detail='Local memory authentication required')

    @app.get('/health')
    async def health():
        return {'revision': REVISION, **runtime.status()}

    @app.post('/context')
    async def context(query: Query, x_mgfr_memory_key: str = Header(default='')):
        authorize(x_mgfr_memory_key)
        try:
            return await runtime.context(query.text, query.user_id, query.character_id)
        except Exception:
            raise HTTPException(503, detail='Memory retrieval temporarily unavailable') from None

    @app.post('/turns')
    async def turn(turn: Turn, x_mgfr_memory_key: str = Header(default='')):
        authorize(x_mgfr_memory_key)
        return runtime.enqueue(turn.event_id, turn.text, turn.user_id, turn.character_id)

    return app
