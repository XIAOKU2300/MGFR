from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService2';new=lab/'VoiceService3'
assert not new.exists()
changes={}
p=Path('app/text.py');s=(old/p).read_text(encoding='utf-8')
a='    text = re.sub(r"。+", "。", text)'
assert s.count(a)==1
s=s.replace(a,a+'\n    text = re.sub(r"([。！？])，+", r"\\1", text)')
s+='''

def prepare_tts_text(text: str) -> str:
    # The installed voice can swallow a short leading clause if several complete
    # sentences share one semantic decode. Preserve those strong boundaries,
    # while commas/colons/hesitation marks stay inside a single sentence.
    return re.sub(r"([。！？])(?=[^。！？])", r"\\1\\n", normalize_for_speech(text))
'''
changes[p]=s
p=Path('app/engines/tts_gptsovits.py');s=(old/p).read_text(encoding='utf-8')
a='from ..text import normalize_for_speech'
assert s.count(a)==1;s=s.replace(a,a+', prepare_tts_text')
a='            "text": normalize_for_speech(text),'
assert s.count(a)==1;s=s.replace(a,'            "text": prepare_tts_text(text),')
changes[p]=s
def ignore(directory,names):
    return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old) in changes]
shutil.copytree(old,new,ignore=ignore)
for p,s in changes.items():
    with (new/p).open('x',encoding='utf-8') as output:output.write(s)
test=(lab/'test_speech2.py').read_text(encoding='utf-8').replace("LAB/'VoiceService2'","LAB/'VoiceService3'")
anchor='    def test_stable_spoken_style_is_added_without_changing_user_messages(self):'
addition='''    def test_tts_breaks_only_complete_sentences(self):
        payload=GptSovitsTts(TtsConfig()).payload('先坐一会儿。事情又不会趁你休息的时候跑掉。')
        self.assertEqual(payload['text'],'先坐一会儿。\\n事情又不会趁你休息的时候跑掉。')
        self.assertNotIn('\\n',GptSovitsTts(TtsConfig()).payload('别着急，慢慢说就好。')['text'])

'''
assert test.count(anchor)==1;test=test.replace(anchor,addition+anchor)
with (lab/'test_speech3.py').open('x',encoding='utf-8') as output:output.write(test)
sample=(lab/'sample_tts.py').read_text(encoding='utf-8').replace("LAB/'VoiceService2'","LAB/'VoiceService3'").replace("LAB/'Samples'","LAB/'Samples3'").replace("LAB/'sample-report.json'","LAB/'sample-report3.json'")
sample=sample.replace("else:server_segments+=len(methods.cut0(payload['text']).splitlines())", "else:server_segments+=len(methods.cut0(payload['text']).splitlines())")
marker="                results.append(row)"
assert sample.count(marker)==1
sample=sample.replace(marker,"""                if variant=='after':
                    required={'01-rest':['先坐一会','事情','跑掉'], '02-punctuation':['我在听','慢慢说','怎么样'], '03-numbers':['12','3.5','26.5','20']}
                    assert all(word in recognized for word in required[name]), 'Synthetic speech lost required words: '+name
"""+marker)
with (lab/'sample_tts3.py').open('x',encoding='utf-8') as output:output.write(sample)
print(new)
