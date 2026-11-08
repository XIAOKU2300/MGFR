from pathlib import Path
import asyncio, json, sys, time, wave
import httpx
import numpy as np

LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService2'))
from app.config import Config
from app.engines.tts_gptsovits import GptSovitsTts, _ResponseAudioParser
from app.engines.asr_sensevoice import SenseVoiceAsr
from app.audio import resample_linear

async def main():
    cfg=Config.load(LAB.parent/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml')
    assert cfg.tts.base_url.rstrip('/')=='http://127.0.0.1:9880'
    tts=GptSovitsTts(cfg.tts);asr=SenseVoiceAsr(cfg.asr);out=[]
    options=[('comma-joined','先坐一会儿，事情又不会趁你休息的时候跑掉。','cut0'),
             ('period-only-split','先坐一会儿。事情又不会趁你休息的时候跑掉。','cut3'),
             ('period-context-seed','先坐一会儿。事情又不会趁你休息的时候跑掉。','cut0')]
    async with httpx.AsyncClient(trust_env=False,timeout=120) as client:
        for name,text,split in options:
            payload=tts.payload(text);payload['text_split_method']=split;payload['seed']=42
            start=time.perf_counter();first=None;pcm=bytearray();parser=_ResponseAudioParser(24000)
            async with client.stream('POST','http://127.0.0.1:9880/tts',json=payload) as response:
                assert response.status_code==200
                async for data in response.aiter_bytes():
                    chunk=parser.feed(data)
                    if chunk and first is None:first=time.perf_counter()-start
                    pcm.extend(chunk)
            assert parser.rate_is_observed
            path=LAB/'Samples'/('short-'+name+'.wav')
            with path.open('xb') as stream:
                with wave.open(stream,'wb') as audio:
                    audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(parser.sample_rate);audio.writeframes(pcm)
            samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
            recognized=asr._transcribe_sync(resample_linear(samples,parser.sample_rate,16000))
            row={'variant':name,'text':text,'transcript':recognized,'seconds':len(samples)/parser.sample_rate,'firstAudioMs':round(first*1000,1)}
            out.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    with (LAB/'short-phrase-check.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)

if __name__=='__main__':asyncio.run(main())
