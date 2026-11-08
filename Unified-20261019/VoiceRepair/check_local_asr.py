"""Local audio-to-text verification; no client, credentials or reply pipeline."""
from pathlib import Path
import asyncio
import ast
import json
import socket
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / 'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService'
sys.path.insert(0, str(SERVICE))

def deny_network(*args, **kwargs):
    raise RuntimeError('Network disabled for the local ASR check')

socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network

import numpy as np
from app.config import AsrConfig
from app.engines.asr_sensevoice import SenseVoiceAsr

async def main():
    started = time.monotonic()
    clip = ROOT / 'HandLab-20261018/VoiceLab-20261018/voice-input.wav'
    with wave.open(str(clip), 'rb') as source:
        assert source.getsampwidth() == 2 and source.getnchannels() == 1
        rate = source.getframerate()
        samples = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768
    engine = SenseVoiceAsr(AsrConfig(
        model_dir=str(ROOT / 'dialogue-service/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17'),
        num_threads=4, language='zh'))
    transcript = await engine.transcribe(samples, rate)
    report = {
        'passed': bool(transcript.strip()), 'engine': engine.name,
        'localOnly': True, 'networkConnectionsBlocked': True,
        'inputSeconds': len(samples) / rate, 'inputSampleRate': rate,
        'recognizedCharacters': len(transcript),
        'elapsedSeconds': round(time.monotonic() - started, 3),
        'transcriptRetained': False, 'headsetMicrophoneTested': False,
    }
    ast.parse((Path(__file__).parent / 'launch_unified.py').read_text(encoding='utf-8'))
    report['launcherPythonSyntaxValid'] = True
    with (Path(__file__).parent / 'local-asr-check.json').open('x', encoding='utf-8') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    if not report['passed']:
        raise SystemExit(1)

if __name__ == '__main__':
    asyncio.run(main())
