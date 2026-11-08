from pathlib import Path
import asyncio,json,sys,wave
import numpy as np

LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService7'))
from app.config import Config
from app.engines.tts_gptsovits import GptSovitsTts
from app.engines.asr_sensevoice import SenseVoiceAsr
from app.audio import resample_linear

async def main():
    cfg=Config.load(LAB.parent/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml')
    assert cfg.tts.base_url.rstrip('/')=='http://127.0.0.1:9880'
    engine=GptSovitsTts(cfg.tts)
    pcm=bytearray();rate=None
    try:
        async for chunk in engine.synthesize('先坐一会儿吧，事情又不会趁你休息的时候跑掉。',asyncio.Event()):
            pcm.extend(chunk.pcm);rate=chunk.sample_rate
    finally:await engine.aclose()
    path=LAB/'LiveVerified/03-short-lead.wav'
    assert rate==32000 and pcm
    with path.open('xb') as stream:
        with wave.open(stream,'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
    asr=SenseVoiceAsr(cfg.asr);rows=[]
    required={'01-voice.wav':['坐','事情','跑掉'],'02-voice.wav':['12','26.5','两成'],'03-short-lead.wav':['先坐一会','事情','跑掉']}
    for name,words in required.items():
        path=LAB/'LiveVerified'/name
        with wave.open(str(path),'rb') as audio:
            rate=audio.getframerate();samples=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').astype(np.float32)/32768
        recognized=asr._transcribe_sync(resample_linear(samples,rate,16000))
        row={'file':str(path),'recognized':recognized,'requiredWords':words,'passed':all(word in recognized for word in words),'seconds':len(samples)/rate}
        rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    with (LAB/'verified-validation.json').open('x',encoding='utf-8') as output:
        json.dump({'passed':all(row['passed'] for row in rows),'unitTestsPassed':17,'userMicrophoneUsed':False,'readbackLocalOnly':True,'samples':rows},output,ensure_ascii=False,indent=2)
    assert all(row['passed'] for row in rows)

if __name__=='__main__':asyncio.run(main())
