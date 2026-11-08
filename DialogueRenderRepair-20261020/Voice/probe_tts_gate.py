"""Diagnose speech verification on known local test lines; no model/user text saved."""
import asyncio
import datetime
import json
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
sys.dont_write_bytecode = True
sys.path.insert(0, str(SERVICE))

async def main():
    namespace = runpy.run_path(str(SERVICE / 'voice_server.py'), run_name='local_tts_verification_probe')
    config = namespace['namespace']['app'].state.config
    from app.engines.factory import build_tts, build_asr
    from app.engines.base import EngineUnavailable
    from app.speech_verify import speech_completeness, numbers, _key, _lcs
    from app.text import prepare_tts_text
    engine = build_tts(config)
    recognizer = build_asr(config)
    current = {'expected': ''}
    rows = []
    class Verify:
        async def transcribe(self, samples, rate):
            actual = await recognizer.transcribe(samples, rate)
            expected = current['expected']
            row = {'expectedChars': len(expected), 'recognizedChars': len(actual), 'expectedNumbers': numbers(expected), 'recognizedNumbers': numbers(actual), 'score': speech_completeness(expected, actual), 'lexicalCoverage': _lcs(_key(expected), _key(actual))/max(1,len(_key(expected))), 'seconds': len(samples)/rate}
            rows[-1]['attempts'].append(row)
            return actual
    engine.verifier = Verify()
    try:
        for label, text in [('greeting', '你好，我是祀。'), ('together', '我们一起出去走走吧。'), ('presence', '我在这里陪你。'), ('memory', '刚才说想和你一起散步。')]:
            for phrase in prepare_tts_text(text).splitlines():
                current['expected'] = phrase
                row = {'case': label, 'attempts': [], 'pcmBytes': 0, 'rejected': False}
                rows.append(row)
                try:
                    async for chunk in engine.synthesize(phrase, asyncio.Event()):
                        row['pcmBytes'] += len(chunk.pcm)
                except EngineUnavailable:
                    row['rejected'] = True
                print(json.dumps(row), flush=True)
    finally:
        await engine.aclose()
    output = HERE / ('tts-gate-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump({'cases': rows, 'contentSaved': False}, stream, indent=2)
    print(str(output))

if __name__ == '__main__':
    asyncio.run(main())
