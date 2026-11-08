from pathlib import Path
import asyncio,json,sys
import numpy as np
LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService9'))
from app.config import Config
from app.engines.tts_gptsovits import GptSovitsTts
from app.engines.asr_sensevoice import SenseVoiceAsr
from app.speech_verify import speech_completeness

async def main():
    cfg=Config.load(LAB.parent/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml')
    engine=GptSovitsTts(cfg.tts);asr=SenseVoiceAsr(cfg.asr);rows=[]
    variants=[{'seed':1},{'seed':19},{'seed':0,'top_k':5,'top_p':1.,'temperature':1.,'repetition_penalty':1.35},
              {'seed':0,'top_k':1,'top_p':1.,'temperature':1.,'repetition_penalty':1.35},
              {'seed':0,'text':'。先歇着吧。'},{'seed':7,'text':'。先歇着吧。'}]
    try:
        for options in variants:
            chunks=[chunk async for chunk in engine._stream('先歇着吧。',engine._epoch,asyncio.Event(),options)]
            pcm=b''.join(chunk.pcm for chunk in chunks);rate=chunks[0].sample_rate
            recognized=await asr.transcribe(np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768,rate)
            row={'options':options,'recognized':recognized,'completeness':speech_completeness('先歇着吧。',recognized),'seconds':len(pcm)/(rate*2)}
            rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    finally:await engine.aclose()
    with (LAB/'short-onset-diagnosis.json').open('x',encoding='utf-8') as output:json.dump(rows,output,ensure_ascii=False,indent=2)

if __name__=='__main__':asyncio.run(main())
