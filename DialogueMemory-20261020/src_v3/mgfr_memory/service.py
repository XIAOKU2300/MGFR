"""Loopback-only memory API. No private config, API key, or transcript logging."""
import contextlib
import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import REVISION
from .remote_runtime import Runtime


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
        return {'revision': REVISION, 'build': os.environ.get('MGFR_MEMORY_BUILD'),
                'store': os.environ.get('MGFR_MEMORY_STORE'), **runtime.status()}

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

    @app.get('/memories')
    async def memories(user_id: str = 'owner', character_id: str = 'si', x_mgfr_memory_key: str = Header(default='')):
        authorize(x_mgfr_memory_key)
        return await runtime.user.get_all(filters={'user_id': user_id, 'agent_id': character_id, 'active': True}, top_k=200)

    @app.post('/knowledge/reload')
    async def reload_knowledge(x_mgfr_memory_key: str = Header(default='')):
        authorize(x_mgfr_memory_key)
        try:
            await runtime.import_knowledge()
            return {'reloaded': True}
        except Exception:
            raise HTTPException(422, detail='Knowledge reload failed; check entry IDs and text') from None

    class Forget(BaseModel):
        memory_id: str = Field(pattern=r'^[a-fA-F0-9-]{36}$')
        user_id: str = 'owner'
        character_id: str = 'si'

    @app.post('/memories/forget')
    async def forget(value: Forget, x_mgfr_memory_key: str = Header(default='')):
        authorize(x_mgfr_memory_key)
        item = await runtime.user.get(value.memory_id)
        if not item or item.get('user_id') != value.user_id or item.get('agent_id') != value.character_id:
            raise HTTPException(404, detail='Memory does not belong to this user and character')
        await runtime.user.delete(value.memory_id)
        return {'forgotten': True, 'meaning': 'removed from recall; local Mem0 audit history is retained'}

    return app
