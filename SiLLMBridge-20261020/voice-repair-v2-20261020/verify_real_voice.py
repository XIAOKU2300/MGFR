"""Verify installed real engines and one JSON-first voice turn without a mic."""
from pathlib import Path
import asyncio
import json
import os
import subprocess
import sys
import time
import wave
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT.parent / 'dialogue-service/.venv/Scripts/python.exe'
OUT = Path(__file__).resolve().parent
OPENER = build_opener(ProxyHandler({}))
EXPECTED = {'vad': 'silero', 'asr': 'sensevoice', 'llm': 'openai', 'tts': 'gptsovits'}


def get(port, path):
    with OPENER.open(f'http://127.0.0.1:{port}{path}', timeout=2) as response:
        return json.load(response)


async def check_turn():
    import websockets
    from app import protocol
    result = {'hello_ack': False, 'listening': False, 'avatar_plan': False,
              'tts_frames': 0, 'tts_bytes': 0, 'tts_end': False,
              'returned_to_listening': False, 'errors': []}
    reply = ''
    async with websockets.connect('ws://127.0.0.1:8774/ws', max_size=None) as ws:
        for kind in ['hello', 'session.start']:
            await ws.send(json.dumps({'v': 1, 'type': kind, 'client': 'real-voice-repair-check'}))
        async with asyncio.timeout(15):
            while not result['listening']:
                msg = json.loads(await ws.recv())
                if msg.get('type') == 'error':
                    raise RuntimeError('Handshake engine failure: ' + str(msg.get('code')))
                if msg.get('type') == 'hello.ack':
                    result['hello_ack'] = True
                if msg.get('type') == 'state' and msg.get('state') == 'listening':
                    result['listening'] = True
        print('Real WebSocket handshake and listening state: OK', flush=True)
        await ws.send(json.dumps({'v': 1, 'type': 'text.input',
                                  'text': '用一句简短中文告诉我你已经恢复连接。'}, ensure_ascii=False))
        async with asyncio.timeout(100):
            while not result['returned_to_listening']:
                data = await ws.recv()
                if isinstance(data, bytes):
                    frame = protocol.decode_audio_frame(data)
                    if frame.kind == protocol.AudioKind.TTS:
                        result['tts_frames'] += 1
                        result['tts_bytes'] += len(frame.payload)
                    continue
                msg = json.loads(data)
                kind = msg.get('type')
                if kind == 'error':
                    result['errors'].append(str(msg.get('code')))
                    raise RuntimeError('Real voice round failed: ' + str(msg.get('code')))
                if kind == 'avatar.plan':
                    result['avatar_plan'] = True
                    result['emotion'] = msg.get('emotion')
                    result['expression'] = msg.get('expression')
                    result['actions'] = msg.get('actions')
                    print('Real LLM JSON accepted; emotion/action plan received', flush=True)
                elif kind == 'llm.delta':
                    reply += msg.get('text', '')
                elif kind == 'tts.end':
                    result['tts_end'] = True
                elif kind == 'state' and msg.get('state') == 'listening' and result['tts_end']:
                    result['returned_to_listening'] = True
        await ws.send(json.dumps({'v': 1, 'type': 'session.end'}))
    result['reply_text_only'] = bool(reply.strip()) and not reply.lstrip().startswith(('{', '```'))
    assert result['avatar_plan'] and result['tts_bytes'] > 0 and result['reply_text_only']
    return result


def main():
    children, streams = [], []
    result = {'real_engines': True, 'microphone_used': False, 'headset_tested': False}
    try:
        for script, port, path, label in [
            (ROOT / 'main_bridge_final.py', 18766, '/v1/catalog', 'actions'),
            (ROOT / 'MainVoice-v1/voice_actions_server.py', 8774, '/health', 'voice')]:
            try:
                health = get(port, path)
            except OSError:
                stream = (OUT / (label + '.log')).open('xb')
                streams.append(stream)
                env = os.environ.copy()
                env['PYTHONUTF8'] = '1'
                env['NO_PROXY'] = '127.0.0.1,localhost'
                child = subprocess.Popen([str(PYTHON), '-B', '-X', 'utf8', str(script)],
                                         cwd=script.parent, env=env, stdout=stream, stderr=stream,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                children.append(child)
                deadline = time.monotonic() + 60
                while True:
                    try:
                        health = get(port, path)
                        break
                    except OSError:
                        if child.poll() is not None or time.monotonic() >= deadline:
                            raise RuntimeError(label + ' startup failed') from None
                        time.sleep(.2)
            if label == 'voice':
                assert health['status'] == 'ok', 'Real engines did not load'
                assert health['engines'] == EXPECTED
                result['health'] = {key: health[key] for key in ['status', 'engines']}
                print('Real Silero / SenseVoice / LLM / GPT-SoVITS engines loaded: OK', flush=True)
            else:
                assert health.get('target') == 'MGFR main project existing character'
        get(9880, '/voice_info')
        sys.path.insert(0, str(ROOT / 'MainVoice-v1'))
        from app.config import AsrConfig, VadConfig
        from app.engines.asr_sensevoice import SenseVoiceAsr
        from app.engines.vad_silero import SileroVad
        import numpy as np
        model_dir = ROOT.parent / 'dialogue-service/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17'
        with wave.open(str(model_dir / 'test_wavs/zh.wav'), 'rb') as audio:
            rate = audio.getframerate()
            samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2').astype(np.float32) / 32768
        vad = SileroVad(VadConfig())
        vad_events = []
        for start in range(0, len(samples), 320):
            event = vad.push(samples[start:start + 320], rate)
            if event.name != 'NONE':
                vad_events.append(event.name)
        result['vad_speech_detected'] = 'SPEECH_START' in vad_events
        asr = SenseVoiceAsr(AsrConfig(model_dir=str(model_dir)))
        result['asr_nonempty_transcript'] = bool(asyncio.run(asr.transcribe(samples, rate)).strip())
        assert result['vad_speech_detected'] and result['asr_nonempty_transcript']
        print('Real local speech sample: VAD detection and ASR transcription OK', flush=True)
        result['voice_turn'] = asyncio.run(check_turn())
        result['pass'] = True
        with (OUT / 'result.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        for stream in streams:
            stream.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Verification failed:', type(error).__name__, flush=True)
        raise SystemExit(1)
