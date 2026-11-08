from pathlib import Path
import asyncio
import json
import sys
import threading
from types import SimpleNamespace
import unittest
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'MainVoice-v1'))
from app import pipeline, structured_avatar
from app.engines.base import AudioChunk
from main_bridge import make_server


class FakeLlm:
    def __init__(self, content):
        self.content = content
        self.finished = False

    async def stream(self, messages, cancel):
        assert 'JSON Schema' in messages[0]['content']
        for i in range(0, len(self.content), 9):
            yield self.content[i:i + 9]
            await asyncio.sleep(0)
        self.finished = True


class FakeTts:
    def __init__(self, session):
        self.session = session
        self.texts = []

    async def synthesize(self, text, cancel):
        assert self.session.engines.llm.finished, 'TTS ran before complete model JSON'
        assert any(e.get('type') == 'avatar.plan' for e in self.session.events), 'Plan not delivered before speech'
        self.texts.append(text)
        yield AudioChunk(pcm=b'\x10\x00' * 320, sample_rate=16000, channels=1)


class FakeSession:
    def __init__(self, content):
        self.events = []
        self.audio = []
        self.engines = SimpleNamespace(llm=FakeLlm(content))
        self.engines.tts = FakeTts(self)
        self.current = True

    async def emit_json(self, value):
        self.events.append(value)

    async def emit_audio(self, value):
        self.audio.append(value)

    async def set_state(self, *args):
        pass

    def build_messages(self, text):
        return [{'role': 'user', 'content': text}]

    def is_current(self, round_):
        return self.current and not round_.cancel.is_set()

    def next_tts_seq(self, round_):
        round_.tts_seq += 1
        return round_.tts_seq


class VoiceIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        catalog = json.loads((ROOT / 'MainData/catalog.json').read_text(encoding='utf-8'))
        self.server = make_server(catalog, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        structured_avatar.URL = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def round(self):
        return SimpleNamespace(id=7, cancel=asyncio.Event(), assistant_text='', tts_seq=0)

    async def test_real_pipeline_only_speaks_text_and_delivers_emotion_action_before_pcm(self):
        value = {'version': 1, 'text': '我有一点难过，不过我会陪着你。', 'emotion': 'sad',
                 'emotion_intensity': .5, 'actions': [{'name': 'think', 'at': 0}]}
        session = FakeSession(json.dumps(value, ensure_ascii=False))
        round_ = self.round()
        result = await pipeline._think_and_speak(session, round_, '你还好吗？')
        self.assertTrue(result)
        self.assertEqual(round_.assistant_text, value['text'])
        self.assertEqual(''.join(session.engines.tts.texts), value['text'])
        self.assertTrue(session.audio)
        self.assertNotIn('emotion', ''.join(session.engines.tts.texts))
        with urlopen(structured_avatar.URL + '/v1/player/plan') as response:
            plan = json.load(response)
        self.assertEqual(plan['voice_round'], 7)
        self.assertEqual(plan['emotion'], 'sad')
        self.assertEqual(plan['actions'][0]['name'], 'think')

    async def test_malformed_model_json_is_not_spoken_or_executed(self):
        session = FakeSession('```json\n{"text":"unsafe wrapper"}\n```')
        result = await pipeline._think_and_speak(session, self.round(), 'test')
        self.assertFalse(result)
        self.assertEqual(session.engines.tts.texts, [])
        self.assertIsNone(self.server.bridge.current)

    async def test_unknown_action_is_not_spoken_or_executed(self):
        session = FakeSession(json.dumps({'version': 1, 'text': '正常台词', 'emotion': 'sad',
                                         'actions': [{'name': '../../bad', 'at': 0}]}))
        result = await pipeline._think_and_speak(session, self.round(), 'test')
        self.assertFalse(result)
        self.assertFalse(session.audio)
        self.assertIsNone(self.server.bridge.current)

    async def test_cancelled_round_cannot_publish_a_plan(self):
        session = FakeSession(json.dumps({'version': 1, 'text': '不要播', 'emotion': 'sad', 'actions': []}))
        round_ = self.round()
        round_.cancel.set()
        result = await structured_avatar.collect_avatar_reply(session, round_, [])
        self.assertIsNone(result)
        self.assertIsNone(self.server.bridge.current)


if __name__ == '__main__':
    unittest.main(verbosity=2)
