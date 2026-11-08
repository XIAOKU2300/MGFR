from pathlib import Path
import asyncio,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent/'VoiceService9'))
from app.config import TtsConfig
from app.engines.tts_gptsovits import GptSovitsTts
from app.engines.base import AudioChunk,EngineUnavailable

class FakeEngine(GptSovitsTts):
    def __init__(self):super().__init__(TtsConfig());self.requests=0
    async def _stream(self,text,epoch,cancel,options=None):
        self.requests+=1
        yield AudioChunk(b'\1\0'*640,32000,1)

class QualityGuards(unittest.IsolatedAsyncioTestCase):
    async def test_all_bad_attempts_are_bounded_and_never_played(self):
        class Verifier:
            async def transcribe(self,samples,rate):return '嗯。'
        engine=FakeEngine();engine.verifier=Verifier();played=[]
        with self.assertRaises(EngineUnavailable):
            async for chunk in engine.synthesize('先歇着吧。',asyncio.Event()):played.append(chunk)
        self.assertEqual(engine.requests,4);self.assertEqual(played,[])
        self.assertEqual(engine.quality_retries,3);self.assertEqual(engine.verified_phrases,0)

    async def test_cancel_during_readback_does_not_release_buffered_audio(self):
        cancel=asyncio.Event()
        class Verifier:
            async def transcribe(self,samples,rate):cancel.set();return '先歇着吧。'
        engine=FakeEngine();engine.verifier=Verifier()
        played=[chunk async for chunk in engine.synthesize('先歇着吧。',cancel)]
        self.assertEqual(engine.requests,1);self.assertEqual(played,[])

    async def test_stale_epoch_during_readback_does_not_release_buffered_audio(self):
        engine=FakeEngine()
        class Verifier:
            async def transcribe(self,samples,rate):engine.invalidate();return '先歇着吧。'
        engine.verifier=Verifier()
        played=[chunk async for chunk in engine.synthesize('先歇着吧。',asyncio.Event())]
        self.assertEqual(engine.requests,1);self.assertEqual(played,[])

if __name__=='__main__':unittest.main(verbosity=2)
