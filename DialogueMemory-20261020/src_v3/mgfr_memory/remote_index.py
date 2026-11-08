"""Bounded Qwen shadow index; the existing Mem0 facts remain authoritative.

Fresh queries can finish in the background. Foreground callers never wait for
the provider beyond their remaining budget. A query vector cache does not cache
recall results: active IDs and user/character scope are checked on every search.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import sqlite3
import time
from collections import OrderedDict
from pathlib import Path

import httpx
import numpy as np

from .credential_store import load

MODEL = 'Qwen/Qwen3-Embedding-8B'
DIMS = 4096
INSTRUCT = 'Instruct: Retrieve relevant character background and user preferences.\nQuery: '


class RemoteIndex:
    def __init__(self, data, config):
        config = Path(config)
        options = json.loads(config.read_text(encoding='utf-8'))
        if options['base_url'] != 'https://emrank.tech/v1' or options['model'] != MODEL or options['dimensions'] != DIMS:
            raise ValueError('Embedding configuration differs from the verified provider')
        credential = config.parent / options['credential_file']
        if credential.resolve().parent != config.parent.resolve():
            raise ValueError('Credential must stay inside the private configuration folder')
        self.allow_query_text = options.get('allow_query_text', False) is True
        self.key = load(credential)
        self.client = httpx.AsyncClient(base_url=options['base_url'], trust_env=False,
            timeout=httpx.Timeout(6, connect=2), limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
            headers={'Authorization': 'Bearer ' + self.key})
        self.path = Path(data) / 'qwen-shadow-4096-v1.sqlite3'
        self.db = sqlite3.connect(self.path)
        self.db.execute('CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, digest TEXT, row_json TEXT, vector BLOB)')
        self.db.commit()
        self.records = {}
        for ident, digest, raw, vector in self.db.execute('SELECT id,digest,row_json,vector FROM vectors'):
            row = json.loads(raw)
            values = np.frombuffer(vector, dtype='<f4').copy()
            if len(values) == DIMS and np.isfinite(values).all():
                self.records[ident] = (digest, row, values)
        self.active = set()  # Authoritative snapshot required before cached records can be recalled.
        self.cache = OrderedDict()
        self.pending = {}
        self.tasks = set()
        self.closed = False
        self.cooldown_until = 0
        self.failures = 0
        self.last_failure = None
        self.document_lock = asyncio.Lock()
        self.query_slots = asyncio.Semaphore(1)
        self.metrics = {'requests': 0, 'cacheHits': 0, 'fallbacks': 0, 'successfulRequests': 0}

    def status(self):
        return {'model': MODEL, 'dimensions': DIMS, 'mode': 'bounded-cache-first-shadow', 'scope': 'role_knowledge_only', 'queryTextAllowed': self.allow_query_text,
                'indexedActive': len(self.active & self.records.keys()), 'activeDocuments': len(self.active),
                'pendingQueries': len(self.pending), 'lastFailureType': self.last_failure,
                'cooldown': time.monotonic() < self.cooldown_until, **self.metrics}

    async def embed(self, texts):
        if self.closed or time.monotonic() < self.cooldown_until:
            raise RuntimeError('Embedding temporarily deferred')
        self.metrics['requests'] += 1
        try:
            response = await self.client.post('/embeddings', json={
                'model': MODEL, 'input': texts, 'encoding_format': 'float'})
            if response.status_code != 200:
                raise RuntimeError('Embedding provider unavailable')
            values = response.json()['data']
            if len(values) != len(texts) or sorted(x['index'] for x in values) != list(range(len(texts))):
                raise ValueError('Embedding row ordering invalid')
            vectors = []
            for item in sorted(values, key=lambda x: x['index']):
                raw = item['embedding']
                if len(raw) != DIMS or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in raw):
                    raise ValueError('Embedding vector invalid')
                vec = np.asarray(raw, dtype='<f4')
                norm = float(np.linalg.norm(vec))
                if not math.isfinite(norm) or norm < 1e-8:
                    raise ValueError('Embedding vector has no direction')
                vectors.append(vec / norm)
            self.failures = 0
            self.last_failure = None
            self.metrics['successfulRequests'] += 1
            return vectors
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.last_failure = type(error).__name__
            self.failures += 1
            self.cooldown_until = time.monotonic() + min(120, 15 * 2 ** min(self.failures-1, 3))
            # Never forward upstream bodies, URLs containing credentials, or exception strings.
            raise RuntimeError('Embedding provider temporarily unavailable') from None

    @staticmethod
    def digest(row):
        return hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()

    async def sync(self, rows):
        if len(rows) > 2000:
            raise ValueError('Remote index snapshot exceeds the bounded capacity')
        async with self.document_lock:
            self.active = {row['id'] for row in rows}
            changed = [row for row in rows if row['id'] not in self.records or self.records[row['id']][0] != self.digest(row)]
            # A changed/retired fact must stop appearing even if re-embedding fails.
            self.active -= {row['id'] for row in changed}
            for offset in range(0, len(changed), 8):
                if self.closed:
                    return
                batch = changed[offset:offset+8]
                vectors = await self.embed([row['text'] for row in batch])
                for row, vector in zip(batch, vectors):
                    digest = self.digest(row)
                    self.db.execute('INSERT OR REPLACE INTO vectors VALUES (?,?,?,?)',
                        (row['id'], digest, json.dumps(row, ensure_ascii=False), vector.astype('<f4').tobytes()))
                    self.records[row['id']] = (digest, row, vector)
                    self.active.add(row['id'])
                self.db.commit()
                await asyncio.sleep(0)

    async def _query(self, text, key):
        try:
            async with self.query_slots:
                vector = (await self.embed([INSTRUCT + text[:1800]]))[0]
            self.cache[key] = vector
            self.cache.move_to_end(key)
            while len(self.cache) > 256:
                self.cache.popitem(last=False)
            return vector
        except (RuntimeError, ValueError):
            return None
        finally:
            self.pending.pop(key, None)

    async def query_vector(self, text, budget_ms):
        if not self.allow_query_text:
            self.metrics['fallbacks'] += 1
            return None
        key = hashlib.sha256(text[:1800].encode('utf-8')).hexdigest()
        if key in self.cache:
            self.metrics['cacheHits'] += 1
            self.cache.move_to_end(key)
            return self.cache[key]
        if self.closed or time.monotonic() < self.cooldown_until:
            self.metrics['fallbacks'] += 1
            return None
        task = self.pending.get(key)
        if task is None:
            if len(self.pending) >= 4:
                self.metrics['fallbacks'] += 1
                return None
            task = asyncio.create_task(self._query(text, key), name='mgfr-qwen-query')
            self.pending[key] = task
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        try:
            async with asyncio.timeout(max(0, budget_ms) / 1000):
                return await asyncio.shield(task)
        except TimeoutError:
            self.metrics['fallbacks'] += 1
            return None

    async def search(self, text, user_id, character_id, budget_ms=60):
        vector = await self.query_vector(text, budget_ms)
        if vector is None:
            return None
        snapshot = [value for key, value in self.records.items() if key in self.active
                    and value[1]['character'] == character_id
                    and (value[1]['kind'] == 'knowledge' or value[1]['user'] == user_id)]
        def rank():
            scored = [(float(np.dot(vector, value[2])), value[1]) for value in snapshot]
            scored.sort(key=lambda x: x[0], reverse=True)
            result = {'memories': [], 'knowledge': []}
            for score, row in scored:
                kind = 'knowledge' if row['kind'] == 'knowledge' else 'memories'
                if score < .30 or len(result[kind]) >= (3 if kind == 'knowledge' else 4):
                    continue
                result[kind].append({'id': row['id'], 'text': row['text'][:220],
                                     'source': row['source'], 'recordedAt': row.get('recordedAt')})
            return result
        return await asyncio.to_thread(rank)

    async def close(self):
        self.closed = True
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*list(self.tasks), return_exceptions=True)
        await self.client.aclose()
        self.db.close()
        self.key = ''
