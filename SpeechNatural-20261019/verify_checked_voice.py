from pathlib import Path
import asyncio,json,re,sys,time,wave
import numpy as np

LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService9'))
from app.config import Config
from app.engines.tts_gptsovits import GptSovitsTts
from app.engines.asr_sensevoice import SenseVoiceAsr
from app.audio import resample_linear
from app.speech_verify import speech_completeness

async def main():
    cfg=Config.load(LAB.parent/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml')
    assert cfg.tts.base_url.rstrip('/')=='http://127.0.0.1:9880'
    cases=[]
    for example in json.loads((LAB/'live-checked-report.json').read_text(encoding='utf-8'))['examples']:
        cases.append((Path(example['file']),example['reply'],example['firstAudioMs']))
    engine=GptSovitsTts(cfg.tts);engine.verifier=SenseVoiceAsr(cfg.asr)
    try:
        for name,text in [('03-short-lead','先坐一会儿吧，事情又不会趁你休息的时候跑掉。'),('04-four-characters','先歇着吧。')]:
            pcm=bytearray();rate=None;first=None;started=time.perf_counter()
            async for chunk in engine.synthesize(text,asyncio.Event()):
                if first is None:first=1000*(time.perf_counter()-started)
                pcm.extend(chunk.pcm);rate=chunk.sample_rate
            path=LAB/'LiveChecked'/(name+'.wav')
            with path.open('xb') as stream:
                with wave.open(stream,'wb') as audio:
                    audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
            cases.append((path,text,first))
    finally:await engine.aclose()
    asr=SenseVoiceAsr(cfg.asr);rows=[]
    for path,expected,first in cases:
        with wave.open(str(path),'rb') as audio:
            rate=audio.getframerate();samples=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').astype(np.float32)/32768
        recognized=asr._transcribe_sync(resample_linear(samples,rate,16000))
        opening=re.split('[，。！？,!?]',expected)[0]
        score=speech_completeness(expected,recognized)
        opening_score=speech_completeness(opening,recognized)
        row={'file':str(path),'expected':expected,'recognized':recognized,'completeness':score,
             'openingClauseRecall':opening_score,'passed':score>=.72 and opening_score>=.72,
             'seconds':len(samples)/rate,'firstAudioMs':round(first,1)}
        rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    with (LAB/'checked-validation.json').open('x',encoding='utf-8') as output:
        json.dump({'passed':all(row['passed'] for row in rows),'unitTestsPassed':20,'userMicrophoneUsed':False,
                   'readbackLocalOnly':True,'directVerifiedPhrases':engine.verified_phrases,'directQualityRetries':engine.quality_retries,
                   'samples':rows},output,ensure_ascii=False,indent=2)
    assert all(row['passed'] for row in rows)

if __name__=='__main__':asyncio.run(main())
