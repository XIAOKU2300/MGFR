"""Trace only verification shape on a generated test reply; do not store full text."""
import asyncio
import json
from pathlib import Path
import runpy
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'SpeechNatural-20261019/VoiceService10'),str(ROOT/'DialogueRenderRepair-20261020/Current/Voice')]
async def main():
    app=runpy.run_path(str(ROOT/'SpeechNatural-20261019/VoiceService10/voice_server.py'),run_name='test_readback_shape')['namespace']['app']
    from install_voice_v4 import install
    install(app,'http://127.0.0.1:18768')
    from app import mgfr_avatar_json as adapter
    from app.engines.factory import build_llm,build_tts,build_asr
    from app.engines import tts_gptsovits
    from app.speech_verify import numbers,_key,_lcs
    from app.engines.base import EngineUnavailable
    import httpx
    async with httpx.AsyncClient(trust_env=False) as client:context=(await client.get(adapter.URL+'/v1/context')).json()
    instruction=context['system_prompt']+'\nJSON Schema:\n'+json.dumps(context['json_schema'],ensure_ascii=False)
    llm=build_llm(app.state.config);tts=build_tts(app.state.config);tts.verifier=build_asr(app.state.config)
    original=tts_gptsovits.speech_completeness
    def observe(expected,actual):
        score=original(expected,actual)
        print(json.dumps({'expectedLength':len(expected),'recognizedLength':len(actual),'score':score,'expectedName':'祀' in expected,'expectedNumbers':numbers(expected),'actualNumbers':numbers(actual),'missingHanCharacters':''.join(sorted(set(_key(expected))-set(_key(actual)))),'recognizedOnlyHanCharacters':''.join(sorted(set(_key(actual))-set(_key(expected))))},ensure_ascii=False),flush=True)
        return score
    tts_gptsovits.speech_completeness=observe
    try:
        for _ in range(2):
            adapter.ensure_json_budget(llm)
            raw=''.join([delta async for delta in llm.stream([{'role':'system','content':instruction},{'role':'user','content':'你好，祀，用一句话打个招呼。'}],asyncio.Event())])
            text=adapter.normalize(adapter.decode_reply(raw),context.get('catalog') or {'actions':[]})['text']
            total=0
            try:
                async for chunk in tts.synthesize(text,asyncio.Event()):total+=len(chunk.pcm)
            except EngineUnavailable:print('READBACK_REJECTED',flush=True)
            print('PCM_BYTES',total,flush=True)
    finally:
        await llm.aclose();await tts.aclose()
if __name__=='__main__':asyncio.run(main())
