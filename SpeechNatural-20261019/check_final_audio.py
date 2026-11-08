"""Verify final PCM treatment against previously generated synthetic audio."""
from pathlib import Path
import json,sys,wave
import numpy as np

LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService4'))
from app.config import Config
from app.engines.asr_sensevoice import SenseVoiceAsr
from app.audio import resample_linear
from app.speech_pcm import SpeechPcmSmoother

cfg=Config.load(LAB.parent/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml')
asr=SenseVoiceAsr(cfg.asr)
folder=LAB/'FinalSamples';folder.mkdir()
rows=[]
required={'01-rest':['先坐一会','事情','跑掉'], '02-punctuation':['我在听','慢慢说','怎么样'], '03-numbers':['12','3.5','26.5','20']}
for name in required:
    with wave.open(str(LAB/'Samples3'/(name+'-after.wav')),'rb') as audio:
        rate=audio.getframerate();channels=audio.getnchannels();original=audio.readframes(audio.getnframes())
    smoother=SpeechPcmSmoother(rate,channels)
    pcm=b''.join(smoother.push(original[i:i+997]) for i in range(0,len(original),997))+smoother.flush()
    path=folder/(name+'.wav')
    with path.open('xb') as output:
        with wave.open(output,'wb') as audio:
            audio.setnchannels(channels);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
    samples=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
    recognized=asr._transcribe_sync(resample_linear(samples,rate,16000))
    passed=all(word in recognized for word in required[name])
    row={'case':name,'passed':passed,'file':str(path),'recognized':recognized,'originalSeconds':len(original)/(rate*channels*2),'finalSeconds':len(pcm)/(rate*channels*2),'removedQuietSeconds':smoother.dropped_bytes/(rate*channels*2)}
    rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
with (LAB/'final-audio-check.json').open('x',encoding='utf-8') as output:json.dump({'passed':all(r['passed'] for r in rows),'localOnly':True,'microphoneUsed':False,'samples':rows},output,ensure_ascii=False,indent=2)
assert all(r['passed'] for r in rows)
