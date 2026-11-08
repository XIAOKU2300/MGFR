"""Multiple WS rounds, retry exhaustion and cancellation must return to listening."""
import asyncio
import datetime
import json
from pathlib import Path
import sys
import threading

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
sys.dont_write_bytecode = True
sys.path[:0] = [str(SERVICE), str(HERE)]

def main():
    from app import main as voice_main
    from app.config import Config
    from app.engines.factory import Engines
    from app.engines.stub import EnergyVad, StubAsr, StubTts
    class Llm:
        name = 'bounded-multiround-fixture'
        calls = 0
        async def stream(self, messages, cancel):
            self.calls += 1
            for message in messages:
                if message['role'] == 'assistant':
                    assert isinstance(json.loads(message['content'])['text'], str)
            user = [m['content'] for m in messages if m['role'] == 'user'][-1]
            retry = any(m['role'] == 'system' and '上一请求没有可用回复' in m['content'] for m in messages)
            if user == 'retry' and not retry or user == 'exhaust':
                yield '   \n'
            elif user == 'cancel':
                await asyncio.sleep(5)
                yield '{}'
            else:
                yield json.dumps({'text': '这一轮正常回复。', 'emotion': 'neutral', 'actions': []}, ensure_ascii=False)
    llm = Llm()
    voice_main.build_all = lambda _: Engines(vad=EnergyVad(), asr=StubAsr(), llm=llm, tts=StubTts(realtime=False))
    app = voice_main.create_app(Config())
    import install_voice_v2
    sys.path.append(str(ROOT / 'SiLLMBridge-20261020'))
    from main_bridge_final import make_server
    catalog = json.loads((ROOT / 'SiLLMBridge-20261020/MainData/catalog.json').read_text(encoding='utf-8'))
    # Install catalog filter before constructing bridge, as in the production worker.
    install_voice_v2.install(app, 'http://127.0.0.1:1')
    bridge = make_server(catalog, 0)
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    sys.modules['app.mgfr_avatar_json'].URL = 'http://127.0.0.1:' + str(bridge.server_port)
    from fastapi.testclient import TestClient
    rounds = []
    try:
        with TestClient(app) as client, client.websocket_connect('/ws') as ws:
            ws.send_json({'v': 1, 'type': 'hello', 'client': 'multi-recovery-check'})
            ws.send_json({'v': 1, 'type': 'session.start'})
            while True:
                m = ws.receive()
                if m.get('text'):
                    event = json.loads(m['text'])
                    if event.get('type') == 'state' and event.get('state') == 'listening':
                        break
            for prompt in ['normal', 'retry', 'normal', 'exhaust', 'normal']:
                ws.send_json({'v': 1, 'type': 'text.input', 'text': prompt})
                row = {'case': prompt, 'audioBytes': 0, 'done': False, 'error': False, 'reply': '', 'listening': False}
                for _ in range(5000):
                    message = ws.receive()
                    if message.get('bytes'):
                        row['audioBytes'] += len(message['bytes'])
                        continue
                    event = json.loads(message['text'])
                    row['done'] |= event.get('type') == 'audio.done'
                    row['error'] |= event.get('type') == 'error'
                    if event.get('type') == 'llm.delta':
                        row['reply'] += event.get('text', event.get('delta', ''))
                    if event.get('type') == 'state' and event.get('state') == 'listening':
                        row['listening'] = True
                        break
                assert row['done'] and row['listening']
                assert '刚才那句' not in row['reply']
                if prompt == 'exhaust':
                    assert row['error'] and not row['audioBytes'] and not row['reply']
                else:
                    assert not row['error'] and row['audioBytes'] > 0 and row['reply']
                del row['reply']
                rounds.append(row)
            ws.send_json({'v': 1, 'type': 'text.input', 'text': 'cancel'})
            while True:
                event = ws.receive_json()
                if event.get('type') == 'state' and event.get('state') == 'thinking':
                    break
            ws.send_json({'v': 1, 'type': 'text.input', 'text': 'after cancel'})
            interrupted = completed = False
            while not completed:
                message = ws.receive()
                if not message.get('text'):
                    continue
                event = json.loads(message['text'])
                interrupted |= event.get('type') == 'interrupt'
                completed = event.get('type') == 'state' and event.get('state') == 'listening'
            assert interrupted
            rounds.append({'case': 'cancel_then_next', 'interrupted': interrupted, 'listening': completed})
    finally:
        bridge.shutdown()
        bridge.server_close()
        thread.join(timeout=3)
    output = HERE / ('recovery-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'pass': True, 'llmCalls': llm.calls, 'rounds': rounds, 'externalCalls': False}, stream, indent=2)
    print('RECOVERY_WS_PASS', str(output), flush=True)

if __name__ == '__main__':
    main()
