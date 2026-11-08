"""Real Mem0/CPU embeddings/persistence; synthetic extractor and speech engines."""
from pathlib import Path
import asyncio
import importlib.metadata
import importlib.util
import json
import logging
import os
import statistics
import sys
import time
import types
import traceback
import uuid

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'src_v3'
RUN = HERE / 'Tests' / ('verify-' + uuid.uuid4().hex)
RUN.mkdir(parents=True)
os.environ.update({
    'MEM0_DIR': str(RUN / 'engine'), 'MEM0_TELEMETRY': 'false',
    'MGFR_MEMORY_MODELS': str(HERE / 'Models'),
    'MGFR_MEMORY_MODEL_PATH': str(HERE / 'Models/bge-small-zh-manual-v1'),
    'MGFR_MEMORY_TOKEN': 'synthetic-local-test-token-not-a-provider-key',
    'MGFR_MEMORY_EXTRACT_URL': 'http://127.0.0.1:1/not-used',
    'HF_HUB_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
    'HF_HOME': str(HERE / 'Models/hf-cache'), 'TOKENIZERS_PARALLELISM': 'false',
})
sys.path[:0] = [str(SOURCE), str(HERE.parent / 'SpeechNatural-20261019/VoiceService10')]
logging.disable(logging.CRITICAL)
from loguru import logger
logger.remove()


class SyntheticExtractor:
    calls = 0
    fail = False

    def generate_response(self, messages, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError('Synthetic provider outage')
        body = messages[-1]['content']
        text = '用户喜欢喝热乌龙茶。' if '乌龙茶' in body else '用户周末喜欢骑自行车。'
        return json.dumps({'memory': [{'text': text}]}, ensure_ascii=False)


async def wait_written(runtime, event_id, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = runtime.db.execute('SELECT state FROM jobs WHERE id=?', (event_id,)).fetchone()
        if row and row[0] == 'done':
            return
        await asyncio.sleep(.025)
    raise AssertionError('Background write did not complete: ' + str(runtime.status()))


async def verify():
    from mgfr_memory.runtime import Runtime
    from mgfr_memory.service import create_app
    import httpx
    checks = {}
    runtime = Runtime(RUN / 'store', SOURCE / 'knowledge.zh.json')
    await runtime.start()
    fake = SyntheticExtractor()
    runtime.user.llm = fake
    first = runtime.enqueue('tea-1', '我喜欢喝热乌龙茶，记住这个偏好。', 'owner', 'si')
    assert first['accepted']
    await wait_written(runtime, 'tea-1')
    assert runtime.enqueue('tea-1', '重复请求', 'owner', 'si')['duplicate']
    assert not runtime.enqueue('credential-1', '我的密码是一个测试字符串', 'owner', 'si')['accepted']
    checks['durable_background_write_and_dedup'] = True
    checks['credential_like_content_excluded'] = True

    result = await runtime.context('我平时喜欢喝什么茶？', 'owner', 'si')
    assert any('乌龙茶' in row['text'] for row in result['memories']), result
    other = await runtime.context('喜欢喝什么茶？', 'other-user', 'si')
    assert not other['memories']
    other_role = await runtime.context('喜欢喝什么茶？', 'owner', 'other-role')
    assert not other_role['memories'] and not other_role['knowledge']
    checks['chinese_paraphrase_recall_and_scope_isolation'] = True
    role = await runtime.context('你最拿手的本领是什么？', 'owner', 'si')
    assert any('绘画' in row['text'] for row in role['knowledge']), role
    checks['role_knowledge_semantic_retrieval'] = True
    await runtime.close()

    runtime = Runtime(RUN / 'store', SOURCE / 'knowledge.zh.json')
    await runtime.start()
    runtime.user.llm = fake
    result = await runtime.context('你记得我喜欢什么饮品吗？', 'owner', 'si')
    assert any('乌龙茶' in row['text'] for row in result['memories']), result
    assert runtime.db.execute('SELECT COUNT(*) FROM imports').fetchone()[0] == 6
    checks['restart_retains_memories_and_no_duplicate_lore'] = True
    fake.fail = True
    runtime.enqueue('pending-1', '周末我喜欢骑自行车。', 'owner', 'si')
    await asyncio.sleep(.2)
    assert runtime.db.execute('SELECT state FROM jobs WHERE id=?', ('pending-1',)).fetchone()[0] != 'done'
    await runtime.close()
    runtime = Runtime(RUN / 'store', SOURCE / 'knowledge.zh.json')
    await runtime.start()
    fake.fail = False
    runtime.user.llm = fake
    runtime.db.execute('UPDATE jobs SET next_at=0 WHERE id=?', ('pending-1',))
    runtime.db.commit()
    runtime.wake.set()
    await wait_written(runtime, 'pending-1')
    checks['provider_outage_and_restart_retry'] = True

    # Exercise the actual ASGI request validation and authorization.
    memory_app = create_app(data=RUN / 'unused', knowledge=SOURCE / 'knowledge.zh.json')
    # Route closures own this object; use the already-open store through its methods.
    route_runtime = memory_app.state.memory
    route_runtime.context = runtime.context
    route_runtime.enqueue = runtime.enqueue
    route_runtime.user = runtime.user
    raw_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=memory_app)
    async with raw_client(transport=transport, base_url='http://memory.test') as api:
        bad = await api.post('/context', json={'text': '你好'})
        assert bad.status_code == 401
        good = await api.post('/context', headers={'X-MGFR-Memory-Key': os.environ['MGFR_MEMORY_TOKEN']}, json={'text': '你记得我的饮品偏好吗？'})
        assert good.status_code == 200
        invalid = await api.post('/turns', headers={'X-MGFR-Memory-Key': os.environ['MGFR_MEMORY_TOKEN']}, json={'text': 'x', 'event_id': '../../x'})
        assert invalid.status_code == 422
    checks['asgi_auth_and_request_validation'] = True

    # The real pre-existing pipeline, protocol PCM framing and stub TTS.
    from app import pipeline
    from app.config import Config
    from app.engines.factory import build_all
    from app.main import create_app as voice_app
    from app.session import Session
    captured = []
    synthetic = types.ModuleType('app.mgfr_avatar_json')
    async def collect_reply(session, round_, messages):
        captured.append(messages)
        return '我记得，你喜欢喝热乌龙茶。'
    synthetic.collect_reply = collect_reply
    sys.modules['app.mgfr_avatar_json'] = synthetic
    adapter_path = HERE.parent / 'SpeechNatural-20261019/VoiceRepair/avatar_pipeline.py'
    spec = importlib.util.spec_from_file_location('app.mgfr_avatar_pipeline', adapter_path)
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)
    adapter._speak = pipeline._speak
    pipeline._think_and_speak = adapter._think_and_speak
    cfg = Config()
    engines = build_all(cfg)
    base_session = Session(engines=engines, config=cfg, out=asyncio.Queue())
    baseline_start = time.perf_counter()
    await base_session.begin_text_turn('我喜欢的饮品是什么？')
    await base_session._task
    baseline_ms = (time.perf_counter() - baseline_start) * 1000
    await base_session.close()

    import voice_memory
    def memory_client(*args, **kwargs):
        return raw_client(transport=transport, base_url='http://memory.test', timeout=.5)
    old = voice_memory.httpx.AsyncClient
    voice_memory.httpx.AsyncClient = memory_client
    application = voice_app(cfg)
    try:
        voice_memory.install(application, url='http://memory.test', token=os.environ['MGFR_MEMORY_TOKEN'])
    finally:
        voice_memory.httpx.AsyncClient = old
    session = Session(engines=engines, config=cfg, out=asyncio.Queue())
    start = time.perf_counter()
    await session.begin_text_turn('我喜欢的饮品是什么？')
    await session._task
    upgraded_ms = (time.perf_counter() - start) * 1000
    assert any('reference_data' in row['content'] and '乌龙茶' in row['content'] for row in captured[-1])
    assert len(session._history) == 2
    assert not any('reference_data' in row['content'] for row in session._history)
    items = []
    while not session.out.empty():
        items.append(session.out.get_nowait())
    assert any(isinstance(item, bytes) for item in items), 'Expected original PCM frames'
    messages = [json.loads(item) for item in items if isinstance(item, str)]
    memory_metric = next(m for m in messages if m.get('type') == 'latency' and m.get('stage') == 'memory')
    assert memory_metric['status'] == 'ready'
    assert any(m.get('type') == 'audio.done' for m in messages)
    checks['original_pipeline_context_pcm_and_clean_history'] = True
    await asyncio.sleep(.15)

    # A stalled retriever must not hold up speech or leak reference data into history.
    original_context = route_runtime.context
    async def slow_context(*args):
        await asyncio.sleep(1)
        return {}
    route_runtime.context = slow_context
    await session.begin_text_turn('现在我们继续聊天。')
    await session._task
    pending_messages = []
    while not session.out.empty():
        item = session.out.get_nowait()
        if isinstance(item, str):
            pending_messages.append(json.loads(item))
    timeout_metric = next(m for m in pending_messages if m.get('type') == 'latency' and m.get('stage') == 'memory')
    assert timeout_metric['status'] == 'unavailable' and timeout_metric['processingMs'] < 200, timeout_metric
    checks['retrieval_timeout_preserves_speech'] = True
    route_runtime.context = original_context
    await session.close()
    await asyncio.sleep(.15)
    manual = await runtime.user.add('用户喜欢软糖。', user_id='management-test', agent_id='si', infer=False, metadata={'active':True})
    memory_id = manual['results'][0]['id']
    async with raw_client(transport=transport, base_url='http://memory.test', headers={'X-MGFR-Memory-Key':os.environ['MGFR_MEMORY_TOKEN']}) as api:
        listing = await api.get('/memories', params={'user_id':'management-test'})
        assert listing.status_code == 200 and any(row['id']==memory_id for row in listing.json()['results'])
        wrong = await api.post('/memories/forget', json={'memory_id':memory_id})
        assert wrong.status_code == 404
        forgotten = await api.post('/memories/forget', json={'memory_id':memory_id,'user_id':'management-test'})
        assert forgotten.status_code == 200
        remaining = await runtime.context('喜欢什么糖？', 'management-test', 'si')
        assert not remaining['memories']
    checks['memory_management_scope_and_forget'] = True

    # Editing an existing lore ID updates it without duplication; retired rows
    # remain auditable but are absent from retrieval, and can be restored.
    original_knowledge = runtime.knowledge_file
    entries = json.loads(original_knowledge.read_text(encoding='utf-8'))
    changed = [dict(row) for row in entries]
    changed[0]['text'] += '本条为资料更新测试。'
    edited = RUN / 'knowledge-updated.json'
    with edited.open('x',encoding='utf-8') as f:json.dump(changed[1:], f, ensure_ascii=False)
    runtime.knowledge_file = edited
    await runtime.import_knowledge()
    retired_id = runtime.db.execute('SELECT memory_id FROM imports WHERE id=?',(entries[0]['id'],)).fetchone()[0]
    assert not (await runtime.lore.get(retired_id))['metadata']['active']
    restored = RUN / 'knowledge-restored.json'
    with restored.open('x',encoding='utf-8') as f:json.dump(changed, f, ensure_ascii=False)
    runtime.knowledge_file = restored
    await runtime.import_knowledge()
    row = await runtime.lore.get(retired_id)
    assert row['metadata']['active'] and '资料更新测试' in row['memory']
    assert runtime.db.execute('SELECT COUNT(*) FROM imports').fetchone()[0] == 6
    runtime.knowledge_file = original_knowledge
    await runtime.import_knowledge()
    checks['knowledge_update_retire_restore_without_duplicates'] = True

    timings = []
    for query in ['我喜欢喝什么？', '祀的绘画能力', '十年之约是什么意思？', '宏山科学院', '我周末有什么爱好？']:
        start = time.perf_counter()
        await runtime.context(query, 'owner', 'si')
        timings.append(round((time.perf_counter() - start) * 1000, 2))
    result = {
        'pass': all(checks.values()), 'checks': checks,
        'mode': 'Real Mem0, real CPU Chinese embeddings, real persistent storage and existing PCM pipeline; synthetic extraction LLM and stub TTS; no microphone',
        'versions': {name: importlib.metadata.version(name) for name in ['mem0ai', 'fastembed', 'qdrant-client', 'onnxruntime']},
        'memoryContextMs': timings, 'contextMaxMs': max(timings), 'contextMedianMs': statistics.median(timings),
        'stubBaselineRoundMs': round(baseline_ms, 2), 'stubMemoryRoundMs': round(upgraded_ms, 2),
        'memoryMetric': memory_metric, 'timeoutMetric': timeout_metric,
    }
    await runtime.close()
    with (RUN / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'pass': result['pass'], 'checks': len(checks), 'contextMs': timings, 'result': str(RUN / 'result.json')}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        asyncio.run(verify())
    except Exception as error:
        with (RUN / 'failure.json').open('x', encoding='utf-8') as stream:
            json.dump({'type': type(error).__name__, 'message': str(error)[:1200], 'trace': traceback.format_exc()}, stream, ensure_ascii=False)
        print(json.dumps({'pass': False, 'errorType': type(error).__name__, 'report': str(RUN / 'failure.json')}))
        raise SystemExit(1)
