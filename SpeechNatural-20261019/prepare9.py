from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService8';new=lab/'VoiceService9'
assert not new.exists();changes={}
p=Path('app/engines/tts_gptsovits.py');s=(old/p).read_text(encoding='utf-8')
a='from ..speech_pcm import SpeechPcmSmoother'
assert s.count(a)==1;s=s.replace(a,a+'\nfrom ..speech_verify import speech_completeness\nimport numpy as np')
a='        self._client = None'
assert s.count(a)==1;s=s.replace(a,a+'\n        self.verifier = None\n        self.verified_phrases = 0\n        self.quality_retries = 0')
a='''                async for chunk in self._stream(phrase, epoch, cancel):
                    yield chunk'''
b='''                if self.verifier is None:
                    async for chunk in self._stream(phrase, epoch, cancel):
                        yield chunk
                    continue
                accepted = False
                for attempt, seed in enumerate((None, 0, 7, 42)):
                    if cancel.is_set() or epoch != self._epoch:
                        return
                    options = None if seed is None else {"seed": seed}
                    chunks = [chunk async for chunk in self._stream(phrase, epoch, cancel, options)]
                    if cancel.is_set() or epoch != self._epoch:
                        return
                    if not chunks:
                        continue
                    pcm = b"".join(chunk.pcm for chunk in chunks)
                    rate, channels = chunks[0].sample_rate, chunks[0].channels
                    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32).reshape(-1, channels).mean(axis=1) / 32768
                    recognized = await self.verifier.transcribe(samples, rate)
                    if cancel.is_set() or epoch != self._epoch:
                        return
                    if speech_completeness(phrase, recognized) >= .72:
                        self.verified_phrases += 1
                        for chunk in chunks:
                            if cancel.is_set() or epoch != self._epoch:
                                return
                            yield chunk
                        accepted = True
                        break
                    if attempt < 3:
                        self.quality_retries += 1
                if not accepted:
                    raise EngineUnavailable("Speech completeness check failed after bounded retries; incorrect audio was withheld")'''
assert s.count(a)==1;s=s.replace(a,b)
a='        self, text: str, epoch: int, cancel: asyncio.Event\n'
assert s.count(a)==1;s=s.replace(a,'        self, text: str, epoch: int, cancel: asyncio.Event, options: dict[str, Any] | None = None\n')
a='        async with client.stream("POST", self.endpoint(), json=self.payload(text)) as response:'
b='''        payload = self.payload(text)
        if options:
            payload.update(options)
        async with client.stream("POST", self.endpoint(), json=payload) as response:'''
assert s.count(a)==1;s=s.replace(a,b);changes[p]=s
p=Path('app/engines/factory.py');s=(old/p).read_text(encoding='utf-8')
a='''    return Engines(
        vad=build_vad(cfg),
        asr=build_asr(cfg),
        llm=build_llm(cfg),
        tts=build_tts(cfg),
    )'''
b='''    engines = Engines(vad=build_vad(cfg), asr=build_asr(cfg), llm=build_llm(cfg), tts=build_tts(cfg))
    if cfg.engines.tts in ("gptsovits", "gpt-sovits") and cfg.engines.asr in ("sensevoice", "sherpa"):
        from .asr_sensevoice import SenseVoiceAsr
        # A separate local recognizer keeps assistant speech verification out of
        # the user's live microphone recognizer and conversation history.
        engines.tts.verifier = SenseVoiceAsr(cfg.asr)
    return engines'''
assert s.count(a)==1;changes[p]=s.replace(a,b)
p=Path('app/main.py');s=(old/p).read_text(encoding='utf-8')
assert s.count('natural-phrases-v4')==1;s=s.replace('natural-phrases-v4','natural-phrases-v5')
a='            "speechRevision": "natural-phrases-v5",'
assert s.count(a)==1;s=s.replace(a,a+'''
            "speechQuality": {"verifiedPhrases": getattr(engines.tts, "verified_phrases", 0), "retries": getattr(engines.tts, "quality_retries", 0)} if engines else {},''');changes[p]=s
def ignore(directory,names):return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old) in changes]
shutil.copytree(old,new,ignore=ignore)
for p,s in changes.items():
    with (new/p).open('x',encoding='utf-8') as output:output.write(s)
shutil.copyfile(lab/'Source/speech_verify.py',new/'app/speech_verify.py')
test=(lab/'test_speech8.py').read_text(encoding='utf-8').replace("LAB/'VoiceService8'","LAB/'VoiceService9'")
anchor='class FakeLlm:'
addition='''class CompletenessTests(unittest.TestCase):
    def test_omitted_words_and_numbers_are_rejected(self):
        from app.speech_verify import speech_completeness
        for expected,heard in [('先歇着吧。','嗯。'),('现在是十二点半。','水温26.5度。'),('温度26.5摄氏度。','温度25度。')]:
            self.assertLess(speech_completeness(expected,heard),.72)

    def test_asr_numeric_spelling_and_erhua_are_accepted(self):
        from app.speech_verify import speech_completeness
        for expected,heard in [('现在是十二点半。','啊，现在是12点半。'),('先坐一会儿吧。','先坐一会吧。'),('温度26.5摄氏度。','温度26.5度。'),('进度百分之20。','进度20%。'),('进度两成。','进度20%。')]:
            self.assertGreaterEqual(speech_completeness(expected,heard),.72,(expected,heard))


'''
assert test.count(anchor)==1;test=test.replace(anchor,addition+anchor)
anchor='    async def test_real_adapter_reports_empty_or_silent_audio_without_crashing(self):'
addition='''    async def test_bad_synthesis_is_retried_before_any_audio_is_emitted(self):
        class Verifier:
            def __init__(self):self.calls=0
            async def transcribe(self,samples,rate):
                self.calls+=1;return '嗯。' if self.calls==1 else '先歇着吧。'
        class Engine(GptSovitsTts):
            async def _stream(self,text,epoch,cancel,options=None):
                yield AudioChunk(b'\\1\\0'*640,32000,1)
        engine=Engine(TtsConfig());engine.verifier=Verifier()
        chunks=[chunk async for chunk in engine.synthesize('先歇着吧。',asyncio.Event())]
        self.assertEqual(len(chunks),1);self.assertEqual(engine.quality_retries,1);self.assertEqual(engine.verified_phrases,1)

'''
assert test.count(anchor)==1;test=test.replace(anchor,addition+anchor)
with (lab/'test_speech9.py').open('x',encoding='utf-8') as output:output.write(test)
helper=(lab/'VoiceRepair/launch_voice_v4.py').read_text(encoding='utf-8').replace("SERVICE=DELIVERY/'VoiceService8'","SERVICE=DELIVERY/'VoiceService9'").replace('natural-phrases-v4','natural-phrases-v5')
with (lab/'VoiceRepair/launch_voice_v5.py').open('x',encoding='utf-8') as output:output.write(helper)
check=(lab/'check_live_tuned.py').read_text(encoding='utf-8').replace("LAB/'VoiceService8'","LAB/'VoiceService9'").replace("LAB/'LiveTuned'","LAB/'LiveChecked'").replace("LAB/'live-tuned-check.json'","LAB/'live-checked-report.json'")
with (lab/'check_live_checked.py').open('x',encoding='utf-8') as output:output.write(check)
print(new)
