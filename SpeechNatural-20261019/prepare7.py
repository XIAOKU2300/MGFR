from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService6';new=lab/'VoiceService7'
assert not new.exists();changes={}
p=Path('app/engines/tts_gptsovits.py');s=(old/p).read_text(encoding='utf-8')
a='''            async for chunk in self._stream(text, epoch, cancel):
                yield chunk'''
b='''            # The installed server can omit a short first segment when several
            # newline segments share one request. Issue protected phrases in
            # order, under the same cancellation epoch and serialization lock.
            for phrase in prepare_tts_text(text).splitlines():
                if cancel.is_set() or epoch != self._epoch:
                    return
                async for chunk in self._stream(phrase, epoch, cancel):
                    yield chunk'''
assert s.count(a)==1;changes[p]=s.replace(a,b)
p=Path('app/main.py');s=(old/p).read_text(encoding='utf-8')
assert s.count('natural-phrases-v2')==1;changes[p]=s.replace('natural-phrases-v2','natural-phrases-v3')
def ignore(directory,names):return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old) in changes]
shutil.copytree(old,new,ignore=ignore)
for p,s in changes.items():
    with (new/p).open('x',encoding='utf-8') as output:output.write(s)
test=(lab/'test_speech6.py').read_text(encoding='utf-8').replace("LAB/'VoiceService6'","LAB/'VoiceService7'")
anchor='    async def test_real_adapter_reports_empty_or_silent_audio_without_crashing(self):'
addition='''    async def test_protected_phrases_use_separate_serial_requests(self):
        class Engine(GptSovitsTts):
            def __init__(self):super().__init__(TtsConfig());self.requests=[]
            async def _stream(self,text,epoch,cancel):
                self.requests.append(text)
                yield AudioChunk(b'\\0'*1280,32000,1)
        engine=Engine()
        chunks=[chunk async for chunk in engine.synthesize('先坐一会儿吧，事情又不会趁你休息的时候跑掉。',asyncio.Event())]
        self.assertEqual(engine.requests,['先坐一会儿吧，','事情又不会趁你休息的时候跑掉。'])
        self.assertEqual(len(chunks),2)

'''
assert test.count(anchor)==1;test=test.replace(anchor,addition+anchor)
with (lab/'test_speech7.py').open('x',encoding='utf-8') as output:output.write(test)
helper=(lab/'VoiceRepair/launch_voice_final.py').read_text(encoding='utf-8').replace("SERVICE=DELIVERY/'VoiceService6'","SERVICE=DELIVERY/'VoiceService7'").replace('natural-phrases-v2','natural-phrases-v3')
with (lab/'VoiceRepair/launch_voice_v3.py').open('x',encoding='utf-8') as output:output.write(helper)
check=(lab/'check_live_final.py').read_text(encoding='utf-8').replace("LAB/'VoiceService6'","LAB/'VoiceService7'").replace("LAB/'LiveFinal'","LAB/'LiveVerified'").replace("LAB/'live-final-check.json'","LAB/'live-verified-check.json'")
with (lab/'check_live_verified.py').open('x',encoding='utf-8') as output:output.write(check)
verify=(lab/'verify_final_voice.py').read_text(encoding='utf-8').replace("LAB/'VoiceService6'","LAB/'VoiceService7'").replace("LAB/'LiveFinal", "LAB/'LiveVerified").replace("'final-validation.json'","'verified-validation.json'").replace("'unitTestsPassed':16","'unitTestsPassed':17")
verify=verify.replace("['先坐一会','事情','跑掉']","['先坐一会','事情','跑掉']")
with (lab/'verify_voice_v3.py').open('x',encoding='utf-8') as output:output.write(verify)
print(new)
