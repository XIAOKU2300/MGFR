from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService4';new=lab/'VoiceService5'
assert not new.exists()
rel=Path('app/engines/tts_gptsovits.py');s=(old/rel).read_text(encoding='utf-8')
a='            if smoother is not None and not cancel.is_set() and epoch == self._epoch:'
b='''            if (smoother is None or not smoother.voiced) and not cancel.is_set() and epoch == self._epoch:
                raise EngineUnavailable("GPT-SoVITS returned no speech audio")
'''+a
assert s.count(a)==1;s=s.replace(a,b)
def ignore(directory,names):return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old)==rel]
shutil.copytree(old,new,ignore=ignore)
with (new/rel).open('x',encoding='utf-8') as output:output.write(s)
test=(lab/'test_speech4.py').read_text(encoding='utf-8').replace("LAB/'VoiceService4'","LAB/'VoiceService5'")
anchor='    async def test_punctuation_only_reply_never_calls_tts(self):'
addition='''    async def test_real_adapter_reports_empty_or_silent_audio_without_crashing(self):
        import httpx
        from app.engines.base import EngineUnavailable
        for pcm in (b'',bytes(32000)):
            fmt=struct.pack('<HHIIHH',1,1,32000,64000,2,16)
            body=b'fmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(pcm))+pcm
            wav=b'RIFF'+struct.pack('<I',len(body)+4)+b'WAVE'+body
            client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=wav)),trust_env=False)
            engine=GptSovitsTts(TtsConfig());engine._client=client
            try:
                with self.assertRaises(EngineUnavailable):
                    async for chunk in engine.synthesize('这是一段本机测试。',asyncio.Event()):pass
            finally:await engine.aclose()

'''
assert test.count(anchor)==1;test=test.replace(anchor,addition+anchor)
with (lab/'test_speech5.py').open('x',encoding='utf-8') as output:output.write(test)
print(new)
