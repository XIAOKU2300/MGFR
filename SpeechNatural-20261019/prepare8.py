from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService7';new=lab/'VoiceService8'
assert not new.exists();changes={}
p=Path('app/engines/tts_gptsovits.py');s=(old/p).read_text(encoding='utf-8')
a='            "speed_factor": 1.0,'
b=a+'''
            "top_k": 15,
            "top_p": .85,
            "temperature": .65,
            "repetition_penalty": 1.2,'''
assert s.count(a)==1;changes[p]=s.replace(a,b)
p=Path('app/main.py');s=(old/p).read_text(encoding='utf-8')
assert s.count('natural-phrases-v3')==1;changes[p]=s.replace('natural-phrases-v3','natural-phrases-v4')
def ignore(directory,names):return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old) in changes]
shutil.copytree(old,new,ignore=ignore)
for p,s in changes.items():
    with (new/p).open('x',encoding='utf-8') as output:output.write(s)
test=(lab/'test_speech7.py').read_text(encoding='utf-8').replace("LAB/'VoiceService7'","LAB/'VoiceService8'")
a="        self.assertEqual(payload['speed_factor'],1)"
assert test.count(a)==1
test=test.replace(a,a+"\n        self.assertEqual((payload['top_k'],payload['top_p'],payload['temperature'],payload['repetition_penalty']),(15,.85,.65,1.2))")
with (lab/'test_speech8.py').open('x',encoding='utf-8') as output:output.write(test)
helper=(lab/'VoiceRepair/launch_voice_v3.py').read_text(encoding='utf-8').replace("SERVICE=DELIVERY/'VoiceService7'","SERVICE=DELIVERY/'VoiceService8'").replace('natural-phrases-v3','natural-phrases-v4')
with (lab/'VoiceRepair/launch_voice_v4.py').open('x',encoding='utf-8') as output:output.write(helper)
check=(lab/'check_live_verified.py').read_text(encoding='utf-8').replace("LAB/'VoiceService7'","LAB/'VoiceService8'").replace("LAB/'LiveVerified'","LAB/'LiveTuned'").replace("LAB/'live-verified-check.json'","LAB/'live-tuned-check.json'")
with (lab/'check_live_tuned.py').open('x',encoding='utf-8') as output:output.write(check)
print(new)
