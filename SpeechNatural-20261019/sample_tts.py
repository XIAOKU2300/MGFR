"""Synthetic, local-only before/after samples. No microphone or external LLM."""
from pathlib import Path
import asyncio
import importlib.util
import json
import sys
import time
import wave
import httpx
import numpy as np

LAB=Path(__file__).resolve().parent
ROOT=LAB.parent
sys.path.insert(0,str(LAB/'VoiceService2'))
from app.config import Config
from app.text import split_sentences
from app.engines.tts_gptsovits import GptSovitsTts, _ResponseAudioParser
from app.engines.asr_sensevoice import SenseVoiceAsr
from app.audio import resample_linear

CONFIG=ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml'
CASES=[
    ('01-rest','先坐一会儿。事情又不会趁你休息的时候跑掉。'),
    ('02-punctuation','……我在听。别着急，慢慢说就好。你今天过得怎么样？！'),
    ('03-numbers','现在是12:30，长度3.5cm，温度26.5°C，已经完成20%。'),
]

def silence_stats(pcm,rate):
    audio=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
    hop=max(1,int(rate*.02));n=len(audio)//hop
    if not n:return {'seconds':0}
    rms=np.sqrt(np.mean(audio[:n*hop].reshape(n,hop)**2,axis=1))
    active=np.where(rms>.008)[0]
    internal=[]
    if len(active):
        gap=0
        for value in rms[active[0]:active[-1]+1]:
            if value<.008:gap+=1
            elif gap:
                if gap>=8:internal.append(round(gap*.02,3))
                gap=0
    return {'seconds':round(len(audio)/rate,3),'peak':round(float(np.max(np.abs(audio))),4),
            'internalPausesOver160ms':internal}

async def main():
    cfg=Config.load(CONFIG)
    assert cfg.tts.base_url.rstrip('/')=='http://127.0.0.1:9880'
    target=LAB/'Samples';target.mkdir()
    adapter=GptSovitsTts(cfg.tts)
    asr=SenseVoiceAsr(cfg.asr)
    spec=importlib.util.spec_from_file_location('installed_tts_split',Path('F:/GPT-SoVITS/GPT_SoVITS/TTS_infer_pack/text_segmentation_method.py'))
    methods=importlib.util.module_from_spec(spec);spec.loader.exec_module(methods)
    results=[]
    async with httpx.AsyncClient(trust_env=False,timeout=httpx.Timeout(120,connect=5)) as client:
        voice=(await client.get('http://127.0.0.1:9880/voice_info')).json().get('model_name')
        for name,text in CASES:
            for variant in ('before','after'):
                phrases=[text] if variant=='before' else split_sentences(text)
                pcm=bytearray();observed=None;started=time.perf_counter();first=None;server_segments=0
                for phrase in phrases:
                    payload=adapter.payload(phrase)
                    if variant=='before':
                        payload['text']=phrase;payload['streaming_mode']=2;payload['fragment_interval']=.08
                        payload['overlap_length']=4;payload['min_chunk_length']=16
                        for field in ('text_split_method','speed_factor','batch_size','split_bucket'):payload.pop(field,None)
                        server_segments+=len(methods.cut5(phrase).splitlines())
                    else:server_segments+=len(methods.cut0(payload['text']).splitlines())
                    parser=_ResponseAudioParser(cfg.tts.fallback_sample_rate)
                    async with client.stream('POST','http://127.0.0.1:9880/tts',json=payload) as response:
                        if response.status_code!=200:raise RuntimeError('Local TTS synthesis failed: HTTP '+str(response.status_code))
                        async for data in response.aiter_bytes():
                            chunk=parser.feed(data)
                            if chunk and first is None:first=time.perf_counter()-started
                            pcm.extend(chunk)
                    assert parser.rate_is_observed and parser.channels==1
                    if observed is not None:assert observed==parser.sample_rate
                    observed=parser.sample_rate
                elapsed=time.perf_counter()-started
                file=target/(name+'-'+variant+'.wav')
                with file.open('xb') as stream:
                    with wave.open(stream,'wb') as audio:
                        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(observed);audio.writeframes(pcm)
                samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
                recognized=asr._transcribe_sync(resample_linear(samples,observed,16000))
                row={'case':name,'variant':variant,'file':str(file),'input':text,'spokenPhrases':phrases if variant=='after' else [text],
                     'rate':observed,'firstAudioMs':round(first*1000,1),'synthesisSeconds':round(elapsed,3),
                     'serverSegments':server_segments,'localAsrTranscript':recognized,**silence_stats(pcm,observed)}
                assert recognized.strip() and row['seconds']>1
                results.append(row)
                print(json.dumps({k:v for k,v in row.items() if k not in ('input','spokenPhrases','localAsrTranscript')},ensure_ascii=False),flush=True)
        assert (await client.get('http://127.0.0.1:9880/voice_info')).json().get('model_name')==voice
    with (LAB/'sample-report.json').open('x',encoding='utf-8') as output:
        json.dump({'localOnly':True,'microphoneUsed':False,'voiceModelUnchanged':True,'samples':results},output,ensure_ascii=False,indent=2)

if __name__=='__main__':asyncio.run(main())
