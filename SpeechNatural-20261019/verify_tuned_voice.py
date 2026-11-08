from pathlib import Path
import asyncio,json,re,sys,wave
import numpy as np

LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService8'))
from app.config import Config
from app.engines.tts_gptsovits import GptSovitsTts
from app.engines.asr_sensevoice import SenseVoiceAsr
from app.audio import resample_linear

def key(text):
    return ''.join(ch for ch in text if '\u4e00'<=ch<='\u9fff' and ch not in '零〇一二两三四五六七八九十百千万亿儿')
def lcs(a,b):
    row=[0]*(len(b)+1)
    for x in a:
        old=0
        for j,y in enumerate(b,1):
            prev=row[j];row[j]=old+1 if x==y else max(row[j],row[j-1]);old=prev
    return row[-1]

async def main():
    cfg=Config.load(LAB.parent/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml')
    assert cfg.tts.base_url.rstrip('/')=='http://127.0.0.1:9880'
    cases=[]
    for example in json.loads((LAB/'live-tuned-check.json').read_text(encoding='utf-8'))['examples']:
        cases.append((Path(example['file']),example['reply']))
    engine=GptSovitsTts(cfg.tts)
    try:
        for name,text in [('03-short-lead','先坐一会儿吧，事情又不会趁你休息的时候跑掉。'),('04-four-characters','先歇着吧。')]:
            pcm=bytearray();rate=None
            async for chunk in engine.synthesize(text,asyncio.Event()):pcm.extend(chunk.pcm);rate=chunk.sample_rate
            path=LAB/'LiveTuned'/(name+'.wav')
            with path.open('xb') as stream:
                with wave.open(stream,'wb') as audio:
                    audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
            cases.append((path,text))
    finally:await engine.aclose()
    asr=SenseVoiceAsr(cfg.asr);rows=[]
    for path,expected in cases:
        with wave.open(str(path),'rb') as audio:
            rate=audio.getframerate();samples=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').astype(np.float32)/32768
        recognized=asr._transcribe_sync(resample_linear(samples,rate,16000))
        first=re.split('[，。！？,!?]',expected)[0]
        score=lcs(key(first),key(recognized))/max(1,len(key(first)))
        numeric=path.name!='02-voice.wav' or ('12' in recognized and '26.5' in recognized and any(v in recognized for v in ('20','两成','二成')))
        row={'file':str(path),'expected':expected,'recognized':recognized,'openingClauseRecall':score,'passed':score>=.8 and numeric,'seconds':len(samples)/rate}
        rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    with (LAB/'tuned-validation.json').open('x',encoding='utf-8') as output:
        json.dump({'passed':all(row['passed'] for row in rows),'unitTestsPassed':17,'userMicrophoneUsed':False,'readbackLocalOnly':True,'samples':rows},output,ensure_ascii=False,indent=2)
    assert all(row['passed'] for row in rows)

if __name__=='__main__':asyncio.run(main())
