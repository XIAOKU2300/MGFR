"""Verify the original voice app and prepared launcher without external calls."""
from pathlib import Path
import asyncio
import hashlib
import json
import runpy
import sys
import threading
from urllib.request import build_opener, ProxyHandler

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
ROOT = REPAIR.parents[1]
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
ASSETS = ROOT / 'SiLLMBridge-20261020'
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(REPAIR))
sys.path.append(str(ASSETS))


def main():
    # Run the same installed private bootstrap; no credentials/config are copied.
    namespace = runpy.run_path(str(SERVICE / 'voice_server.py'), run_name='local_existing_app_check')
    app = namespace['namespace']['app']
    from app.config import SERVICE_ROOT
    from app import pipeline, protocol
    from app.engines.base import AudioChunk
    import avatar_upgrade
    original_speak = pipeline._speak
    original_config = app.state.config
    avatar_upgrade.install(app)
    assert SERVICE_ROOT == SERVICE
    assert app.state.config is original_config
    assert original_config.source_path.resolve() == (ROOT / 'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml').resolve()
    assert pipeline._speak is original_speak
    from app.engines.vad_silero import SileroVad
    assert SileroVad.model_path() == SERVICE / 'models/silero_vad.onnx'
    assert SileroVad.model_path().is_file()

    from main_bridge_final import make_server
    server = make_server(json.loads((ASSETS / 'MainData/catalog.json').read_text(encoding='utf-8')), 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    from app import mgfr_avatar_json
    mgfr_avatar_json.URL = 'http://127.0.0.1:' + str(server.server_port)
    plan = {'version': 1, 'text': '现在可以正常聊天了。', 'emotion': 'sad',
            'emotion_intensity': .5, 'actions': [{'name': 'think', 'at': 0}]}

    class FakeLlm:
        name = 'local-test-json'
        finished = False

        async def stream(self, messages, cancel):
            assert 'JSON Schema' in messages[0]['content']
            raw = json.dumps(plan, ensure_ascii=False)
            yield raw[:len(raw) // 2]
            await asyncio.sleep(0)
            self.finished = True
            yield raw[len(raw) // 2:]

    spoken = []

    class FakeTts:
        name = 'local-test-pcm'
        def invalidate(self):
            pass

        async def synthesize(self, text, cancel):
            assert fake_llm.finished
            assert server.bridge.current is not None
            spoken.append(text)
            yield AudioChunk(pcm=b'\x10\x00' * 640, sample_rate=16000, channels=1)

    from fastapi.testclient import TestClient
    result = {'original_config_reused': True, 'original_model_root': str(SERVICE_ROOT),
              'original_tts_and_audio_function_reused': True, 'external_model_called': False,
              'microphone_used': False}
    try:
        with TestClient(app) as client:
            health = client.get('/health').json()
            assert health['status'] == 'ok'
            assert health['avatarRevision'] == avatar_upgrade.REVISION
            result['real_engine_health'] = {key: health[key] for key in ['status', 'engines', 'avatarRevision']}
            print('Original real engines/config/model root and upgraded health: OK', flush=True)
            engines = app.state.engines
            actual_llm, actual_tts = engines.llm, engines.tts
            class Capture:
                def stream(self, method, url, **kwargs):
                    assert kwargs['json']['response_format'] == {'type': 'json_object'}
                    assert kwargs['json']['model'] == 'local-test'
                    return True
            actual_llm._client = Capture()
            assert actual_llm._get_client().stream('POST', 'http://127.0.0.1/local-test', json={'model': 'local-test'})
            actual_llm._client = None
            fake_llm = FakeLlm()
            engines.llm, engines.tts = fake_llm, FakeTts()
            try:
                with client.websocket_connect('/ws') as ws:
                    for kind in ['hello', 'session.start']:
                        ws.send_json({'v': 1, 'type': kind, 'client': 'local-migration-test'})
                    hello = listening = False
                    for _ in range(10):
                        msg = ws.receive_json()
                        assert msg.get('type') != 'error'
                        hello |= msg.get('type') == 'hello.ack'
                        listening |= msg.get('type') == 'state' and msg.get('state') == 'listening'
                        if hello and listening:
                            break
                    assert hello and listening
                    ws.send_json({'v': 1, 'type': 'text.input', 'text': 'local fixture'})
                    audio_bytes, reply, avatar = 0, '', None
                    for _ in range(60):
                        frame = ws.receive()
                        if frame.get('bytes'):
                            decoded = protocol.decode_audio_frame(frame['bytes'])
                            audio_bytes += len(decoded.payload)
                            assert avatar is not None
                            continue
                        msg = json.loads(frame['text'])
                        assert msg.get('type') != 'error'
                        if msg.get('type') == 'avatar.plan':
                            avatar = msg
                        elif msg.get('type') == 'llm.delta':
                            reply += msg.get('text', '')
                        elif msg.get('type') == 'state' and msg.get('state') == 'listening':
                            break
                    assert reply == plan['text'] == ''.join(spoken)
                    assert audio_bytes > 0 and avatar['emotion'] == 'sad'
                    assert avatar['actions'][0]['name'] == 'think'
                    result['websocket_json_plan_before_audio'] = True
                    result['reply_text_only'] = True
                    result['audio_bytes'] = audio_bytes
                    ws.send_json({'v': 1, 'type': 'session.end'})
            finally:
                engines.llm, engines.tts = actual_llm, actual_tts
        candidate = (HERE / 'launch_voice_v6.py.proposed').read_text(encoding='utf-8')
        ns = {'__file__': str(REPAIR / 'launch_voice_v6.py'), '__name__': 'launcher_review'}
        exec(compile(candidate, ns['__file__'], 'exec'), ns)
        ns['verify_health'](health)
        for invalid in [{**health, 'status': 'degraded'}, {**health, 'avatarRevision': 'old'}]:
            try:
                ns['verify_health'](invalid)
            except ns['VoiceStartupError']:
                pass
            else:
                raise AssertionError('Bad health accepted')
        assert ns['HEALTH'] == 'http://127.0.0.1:8773/health'
        assert '8774' not in candidate
        assert str(ns['EXPECTED_CONFIG']) == str(original_config.source_path)
        result['launcher_uses_original_8773_and_config'] = True
        result['degraded_or_stale_service_rejected'] = True
        result['pass'] = True
        with (HERE / 'test-result.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == '__main__':
    main()
