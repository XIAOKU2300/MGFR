from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService'
new=lab/'VoiceService2'
assert not new.exists()
rel=Path('app/text.py')
s=(old/rel).read_text(encoding='utf-8')
a=r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b'
b=r'(?<![\d.])\d{1,3}(?:,\d{3})+(?:\.\d+)?(?![\d.])'
assert s.count(a)==1;s=s.replace(a,b)
a='    text = text.lstrip("，。！？!?;；:：、…—~ ")'
assert s.count(a)==1;s=s.replace(a,a+'.rstrip("，、 ")')
def ignore(directory,names):
    return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old)==rel]
shutil.copytree(old,new,ignore=ignore)
with (new/rel).open('x',encoding='utf-8') as output:output.write(s)
test=(lab/'test_speech.py').read_text(encoding='utf-8').replace("LAB/'VoiceService'","LAB/'VoiceService2'")
with (lab/'test_speech2.py').open('x',encoding='utf-8') as output:output.write(test)
print(new)
