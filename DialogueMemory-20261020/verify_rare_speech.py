"""Inspect original readback on a fixed synthetic lore sentence, no chat request."""
from pathlib import Path
import asyncio
import importlib.util
import json
import runpy
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path[:0]=[str(ROOT/'SpeechNatural-20261019/VoiceService10'),str(ROOT/'DialogueRenderRepair-20261020/Final-v3/Voice')]

async def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--upgrade',action='store_true');args=parser.parse_args()
    namespace=runpy.run_path(str(ROOT/'SpeechNatural-20261019/VoiceService10/voice_server.py'),run_name='rare_speech_original_bootstrap')
    app=namespace['namespace']['app']
    from install_voice_v4 import install
    install(app,'http://127.0.0.1:18772')
    if args.upgrade:
        sys.path.insert(0,str(HERE/'src_v3'))
        from lore_speech import install as install_lore
        install_lore()
    from app.engines.factory import build_all
    from app.engines import tts_gptsovits
    engines=build_all(app.state.config)
    original=tts_gptsovits.speech_completeness
    if args.upgrade:
        assert original('也能驱使墨魉和器伥。','今天天气晴朗。') < .72
        assert original('墨魉有三十个。','墨量有十三个。') == 0
    samples=[]
    def capture(expected,recognized):
        score=original(expected,recognized)
        samples.append({'expected':expected,'readback':recognized,'score':score})
        return score
    tts_gptsovits.speech_completeness=capture
    pcm=0;error=None;began=time.perf_counter()
    try:
        async for chunk in engines.tts.synthesize('也能驱使墨魉和器伥。',asyncio.Event()):pcm+=len(chunk.pcm)
    except Exception as exc:error=type(exc).__name__
    finally:
        for engine in (engines.llm,engines.tts):
            await engine.aclose()
    result={'pass':pcm>0 and error is None,'upgraded':args.upgrade,'samples':samples,'pcmBytes':pcm,'errorType':error,'seconds':round(time.perf_counter()-began,2)}
    out=HERE/'Tests'/('rare-speech-'+uuid.uuid4().hex+'.json')
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'result':str(out),**result},ensure_ascii=False))
    if not result['pass']:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
