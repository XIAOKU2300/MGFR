from pathlib import Path
import asyncio,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent/'VoiceService10'))
from app.config import TtsConfig
from app.engines.tts_gptsovits import GptSovitsTts
from app.engines.base import AudioChunk

class OnsetRecovery(unittest.IsolatedAsyncioTestCase):
    async def test_rejected_short_audio_recovers_without_adding_spoken_words(self):
        class Verifier:
            def __init__(self):self.calls=0
            async def transcribe(self,samples,rate):
                self.calls+=1
                return '嗯。' if self.calls<3 else '先歇着吧。'
        class Engine(GptSovitsTts):
            def __init__(self):super().__init__(TtsConfig());self.options=[]
            async def _stream(self,text,epoch,cancel,options=None):
                self.options.append(options)
                yield AudioChunk(bytes([len(self.options),0])*640,32000,1)
        engine=Engine();engine.verifier=Verifier()
        chunks=[chunk async for chunk in engine.synthesize('先歇着吧。',asyncio.Event())]
        self.assertEqual(len(chunks),1)
        self.assertEqual(chunks[0].pcm,bytes([3,0])*640)
        self.assertEqual(engine.options[2]['text'],'。先歇着吧。')
        self.assertEqual(engine.quality_retries,2)
        self.assertEqual(engine.verified_phrases,1)

if __name__=='__main__':unittest.main(verbosity=2)
