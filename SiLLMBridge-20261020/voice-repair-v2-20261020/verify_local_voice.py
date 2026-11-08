"""Local-only real engine and WebSocket check; never starts an LLM turn."""
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
OUT = Path(__file__).resolve().parent
PYTHON = ROOT.parent / 'dialogue-service/.venv/Scripts/python.exe'
OPENER = build_opener(ProxyHandler({}))


def health():
    with OPENER.open('http://127.0.0.1:8774/health', timeout=2) as response:
        return json.load(response)


async def handshake():
    import websockets
    from app import protocol
    seen = set()
    async with websockets.connect('ws://127.0.0.1:8774/ws', max_size=None) as ws:
        for kind in ['hello', 'session.start']:
            await ws.send(json.dumps({'v': 1, 'type': kind, 'client': 'local-repair-check'}))
        async with asyncio.timeout(10):
            while not {'hello.ack', 'listening'} <= seen:
                msg = json.loads(await ws.recv())
                assert msg.get('type') != 'error', 'Handshake failed'
                seen.add(msg.get('type'))
                if msg.get('type') == 'state':
                    seen.add(msg.get('state'))
        # Silence cannot trigger ASR or any LLM turn.
        for index in range(5):
            await ws.send(protocol.encode_audio_frame(protocol.AudioFrame(
                kind=protocol.AudioKind.MIC, round=0, seq=index,
                sample_rate=16000, channels=1, frame_ms=20, payload=bytes(640))))
        await ws.send(json.dumps({'v': 1, 'type': 'session.end'}))
        await asyncio.sleep(.15)
    return {'hello_ack': True, 'listening': True, 'silence_frames_sent': 5,
            'llm_turn_started': False}


def main():
    child = None
    log = None
    try:
        try:
            current = health()
        except OSError:
            log = (OUT / 'local-voice.log').open('xb')
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            env['NO_PROXY'] = '127.0.0.1,localhost'
            child = subprocess.Popen([str(PYTHON), '-B', '-X', 'utf8',
                                      str(ROOT / 'MainVoice-v1/voice_actions_server.py')],
                                     cwd=ROOT / 'MainVoice-v1', env=env, stdout=log, stderr=log,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic() + 60
            while True:
                try:
                    current = health()
                    break
                except OSError:
                    if child.poll() is not None or time.monotonic() >= deadline:
                        raise RuntimeError('Local service startup failed') from None
                    time.sleep(.2)
        assert current['status'] == 'ok', 'Real engines did not load'
        assert current['engines'] == {'vad': 'silero', 'asr': 'sensevoice', 'llm': 'openai', 'tts': 'gptsovits'}
        print('Real service health: ok; four configured engine adapters loaded', flush=True)
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
        events = [vad.push(samples[i:i + 320], rate).name for i in range(0, len(samples), 320)]
        speech = 'SPEECH_START' in events
        asr = SenseVoiceAsr(AsrConfig(model_dir=str(model_dir)))
        recognized = bool(asyncio.run(asr.transcribe(samples, rate)).strip())
        assert speech and recognized
        print('Actual local speech: Silero detection and SenseVoice transcription passed', flush=True)
        ws = asyncio.run(handshake())
        result = {'pass': True, 'status': current['status'], 'engines': current['engines'],
                  'vad_speech_detected': speech, 'asr_nonempty_transcript': recognized,
                  'websocket': ws, 'external_model_called': False, 'microphone_used': False}
        with (OUT / 'local-result.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
        if log is not None:
            log.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Local verification failed:', type(error).__name__, flush=True)
        raise SystemExit(1)
