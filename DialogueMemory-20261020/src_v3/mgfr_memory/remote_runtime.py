"""Optional remote recall layered on the existing durable local memory engine."""
import asyncio
import os
import time
from pathlib import Path

from .runtime import Runtime as LocalRuntime, SECRET
from .remote_index import RemoteIndex


class Runtime(LocalRuntime):
    def __init__(self, data, knowledge):
        super().__init__(data, knowledge)
        self.remote = None
        self.remote_loop = None
        self.remote_failure = None
        self.remote_requested = False

    async def start(self):
        await super().start()
        default = Path(__file__).resolve().parents[2] / 'secrets/embedding.json'
        config = Path(os.environ.get('MGFR_EMBED_CONFIG', str(default)))
        self.remote_requested = config.exists()
        if not self.remote_requested:
            return
        try:
            # SSL context, DPAPI and SQLite initialization occur before accepting requests.
            self.remote = RemoteIndex(self.data, config)
            self.remote_loop = asyncio.create_task(self.sync_loop(), name='mgfr-qwen-background-index')
        except Exception as error:
            self.remote_failure = type(error).__name__

    async def sync_loop(self):
        while True:
            try:
                # The current application supports one configured owner and Si.
                # Requests for another scope continue through the local engine.
                # Only curated character knowledge may leave this machine.
                # Existing user facts and queued dialogue stay in local Mem0.
                lore = await self.lore.get_all(
                    filters={'agent_id': 'si', 'active': True}, top_k=1001)
                rows = []
                for kind, result in (('knowledge', lore),):
                    if len(result['results']) > 1000:
                        raise ValueError('Remote mirror capacity exceeded; use local recall')
                    for item in result['results']:
                        if SECRET.search(item['memory']):
                            continue
                        metadata = item.get('metadata') or {}
                        rows.append({'id': item['id'], 'kind': kind, 'text': item['memory'][:1800],
                            'user': item.get('user_id', 'owner'), 'character': item.get('agent_id', 'si'),
                            'source': metadata.get('source', 'user_statement'), 'recordedAt': metadata.get('observed_at')})
                await self.remote.sync(rows)
                self.remote_failure = None
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.remote_failure = type(error).__name__
                # Failed snapshots cannot safely serve stale/deleted memories.
                self.remote.active.clear()
            await asyncio.sleep(5)

    async def context(self, query, user_id, character_id):
        started = time.perf_counter()
        local_task = asyncio.create_task(super().context(query, user_id, character_id))
        if self.remote is None or user_id != 'owner' or character_id != 'si' or SECRET.search(query):
            return await local_task
        remote_task = asyncio.create_task(self.safe_remote(query, user_id, character_id))
        try:
            local, remote = await asyncio.gather(local_task, remote_task)
            result = local
            # Remote queries rank the authoritative active snapshot. Fill any
            # remaining slots with local results; do not compare incompatible scores.
            if remote:
                for kind, count in (('memories', 4), ('knowledge', 3)):
                    seen = {row['id'] for row in remote[kind]}
                    result[kind] = (remote[kind] + [row for row in local[kind] if row['id'] not in seen])[:count]
            result['retrieval'] = 'qwen-cache' if remote is not None else 'local-fallback'
            result['processingMs'] = round((time.perf_counter() - started) * 1000, 2)
            return result
        finally:
            for task in (local_task, remote_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(local_task, remote_task, return_exceptions=True)

    async def safe_remote(self, query, user_id, character_id):
        try:
            result = await self.remote.search(query, user_id, character_id, budget_ms=60)
            if result is None:
                return None
            # Revalidate against Mem0 now, so forgotten, retired or edited facts
            # cannot be served during the background mirror's five-second gap.
            for kind, memory in (('memories', self.user), ('knowledge', self.lore)):
                selected = []
                for row in result[kind]:
                    current = await memory.get(row['id'])
                    if not current or current.get('agent_id') != character_id:
                        continue
                    if kind == 'memories' and current.get('user_id') != user_id:
                        continue
                    if not current.get('metadata', {}).get('active') or current.get('memory', '')[:220] != row['text']:
                        continue
                    selected.append(row)
                result[kind] = selected
            return result
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.remote_failure = type(error).__name__
            return None

    def status(self):
        result = super().status()
        result['remoteEmbedding'] = self.remote.status() if self.remote else {
            'configured': self.remote_requested, 'lastFailureType': self.remote_failure}
        result['remoteMirrorFailureType'] = self.remote_failure
        return result

    async def close(self):
        if self.remote_loop:
            self.remote_loop.cancel()
            await asyncio.gather(self.remote_loop, return_exceptions=True)
        if self.remote:
            await self.remote.close()
        await super().close()
