from pathlib import Path
import asyncio
import contextlib
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import sys
import threading
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
sys.path.insert(0, str(SERVICE))
sys.path.append(str(ROOT / 'SiLLMBridge-20261020'))
name = 'app.mgfr_avatar_json'
loader = SourceFileLoader(name, str(HERE / 'avatar_json-final.py.proposed'))
module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader))
sys.modules[name] = module
loader.exec_module(module)
pipeline_loader = SourceFileLoader('app.latest_pipeline_review', str(HERE.parent / 'avatar_pipeline.py'))
pipeline = importlib.util.module_from_spec(importlib.util.spec_from_loader(pipeline_loader.name, pipeline_loader))
sys.modules[pipeline_loader.name] = pipeline
pipeline_loader.exec_module(pipeline)
from app.engines.base import AudioChunk
from main_bridge_final import make_server
CATALOG = json.loads((ROOT / 'SiLLMBridge-20261020/MainData/catalog.json').read_text(encoding='utf-8'))


class ParsingTests(unittest.TestCase):
    def test_api_catalog_does_not_advertise_or_substitute_failed_clips(self):
        from bridge_server import Bridge
        bridge = Bridge(CATALOG)
        enabled = {a['name'] for a in bridge.catalog['actions'] if a.get('callable', True)}
        self.assertEqual(enabled, module.REVIEWED_ACTIONS)
        self.assertNotIn('play', enabled)
        self.assertNotIn('relax_react', enabled)

    def test_common_json_deviations_preserve_text_and_bound_metadata(self):
        value = module.decode_reply('```json\n{"text":"可以继续聊。","emotion":"sadness","actions":["think",{"name":"../../bad"}]}\n```')
        plan = module.normalize(value, CATALOG)
        self.assertEqual(plan['text'], '可以继续聊。')
        self.assertEqual(plan['emotion'], 'sad')
        self.assertEqual(plan['actions'], [{'name': 'think', 'at': 0}])

    def test_cut_metadata_and_cut_text_never_read_json_keys(self):
        self.assertEqual(module.decode_reply('{"text":"完整台词。","actions":[')['text'], '完整台词。')
        fallback = module.decode_reply('{"text":"没有结束的台词')
        self.assertNotIn('text', fallback['text'])
        self.assertEqual(module.decode_reply('自然的纯文本台词。')['text'], '自然的纯文本台词。')

    def test_unknown_unhashable_and_unreviewed_actions_are_skipped(self):
        value = {'text': '保留声音。', 'emotion': ['bad'], 'emotion_intensity': float('inf'),
                 'actions': [{'name': {}}, {'name': 'play'}, {'name': 'talk_hands', 'at': -5}]}
        plan = module.normalize(value, CATALOG)
        self.assertEqual(plan['actions'], [{'name': 'talk_hands', 'at': 0}])
        self.assertEqual(plan['emotion'], 'neutral')
        self.assertEqual(plan['emotion_intensity'], .55)


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.server = make_server(CATALOG, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        module.URL = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def session(self, raw):
        class Llm:
            finished = False
            async def stream(self, messages, cancel):
                yield raw
                self.finished = True
        session = SimpleNamespace(events=[], spoken=[], engines=SimpleNamespace(llm=Llm()))
        async def emit_json(value): session.events.append(value)
        async def emit_audio(value): pass
        async def set_state(*args): pass
        class Tts:
            async def synthesize(self, text, cancel):
                assert session.engines.llm.finished
                session.spoken.append(text)
                yield AudioChunk(pcm=b'\x10\x00' * 320, sample_rate=16000, channels=1)
        session.engines.tts = Tts()
        session.emit_json, session.emit_audio, session.set_state = emit_json, emit_audio, set_state
        session.build_messages = lambda text: [{'role': 'user', 'content': text}]
        session.is_current = lambda round_: not round_.cancel.is_set()
        session.next_tts_seq = lambda round_: 1
        return session

    def round(self):
        return SimpleNamespace(id=9, cancel=asyncio.Event(), assistant_text='')

    async def test_invalid_metadata_still_reaches_original_tts_without_error(self):
        session = self.session('{"text":"保留正常对话。","emotion":"bad","expression":"sad_soft","actions":[{"name":"bad","duration":3}]}')
        self.assertTrue(await pipeline._think_and_speak(session, self.round(), 'test'))
        self.assertEqual(''.join(session.spoken), '保留正常对话。')
        self.assertFalse(any(e.get('type') == 'error' for e in session.events))

    async def test_truncated_response_recovers_speech_and_complete_plan(self):
        session = self.session('{"text":"这一句完整的话仍然能朗读。","emotion":')
        self.assertTrue(await pipeline._think_and_speak(session, self.round(), 'test'))
        self.assertEqual(''.join(session.spoken), '这一句完整的话仍然能朗读。')
        self.assertEqual(self.server.bridge.current['plan']['actions'], [])

    async def test_action_api_failure_cannot_block_speech(self):
        module.URL = 'http://127.0.0.1:1'
        session = self.session('{"text":"动作服务失败也保留台词。","emotion":"sad","actions":[]}')
        self.assertTrue(await pipeline._think_and_speak(session, self.round(), 'test'))
        self.assertEqual(''.join(session.spoken), '动作服务失败也保留台词。')

    async def test_cancelled_turn_cannot_publish_or_speak(self):
        session = self.session('{"text":"停止","emotion":"sad","actions":[]}')
        round_ = self.round();round_.cancel.set()
        self.assertIsNone(await module.collect_reply(session, round_, []))
        self.assertIsNone(self.server.bridge.current)
        self.assertFalse(session.spoken)

    async def test_payload_budget_and_finish_reason_without_changing_config(self):
        captured = {}
        engine = SimpleNamespace(cfg=SimpleNamespace(max_tokens=180))
        class Response:
            async def aiter_lines(self):
                yield 'data: {"choices":[{"finish_reason":"length"}]}'
        class Client:
            @contextlib.asynccontextmanager
            async def stream(self, method, url, **kwargs):
                captured.update(kwargs['json'])
                yield Response()
        engine._get_client = lambda: Client()
        module.ensure_json_budget(engine)
        async with engine._get_client().stream('POST', 'http://127.0.0.1/test', json={'max_tokens':180}) as response:
            async for _ in response.aiter_lines(): pass
        self.assertEqual(captured['max_tokens'], 512)
        self.assertEqual(engine.cfg.max_tokens, 180)
        self.assertEqual(engine._mgfr_finish_reason, 'length')


if __name__ == '__main__':
    unittest.main(verbosity=2)
