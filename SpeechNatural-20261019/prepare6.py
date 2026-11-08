from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService5';new=lab/'VoiceService6'
assert not new.exists()
changes={}
p=Path('app/text.py');s=(old/p).read_text(encoding='utf-8')
start=s.index('def prepare_tts_text(text: str) -> str:')
s=s[:start]+'''def prepare_tts_text(text: str) -> str:
    # This installed voice can swallow a very short lead-in before a much longer
    # clause. Protect that one boundary; keep ordinary comma clauses together.
    spoken = normalize_for_speech(text)
    parts = []
    for sentence in re.split(r"(?<=[。！？])", spoken):
        sentence = sentence.strip()
        if not sentence:
            continue
        while '，' in sentence:
            at = sentence.index('，')
            length = sum(unicodedata.category(ch)[0] in 'LN' for ch in sentence[:at])
            if length > 8:
                break
            parts.append(sentence[:at+1])
            sentence = sentence[at+1:].lstrip()
        if sentence:
            parts.append(sentence)
    return '\\n'.join(parts)
'''
changes[p]=s
p=Path('app/main.py');s=(old/p).read_text(encoding='utf-8')
assert s.count('natural-phrases-v1')==1
changes[p]=s.replace('natural-phrases-v1','natural-phrases-v2')
def ignore(directory,names):return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old) in changes]
shutil.copytree(old,new,ignore=ignore)
for p,s in changes.items():
    with (new/p).open('x',encoding='utf-8') as output:output.write(s)
test=(lab/'test_speech5.py').read_text(encoding='utf-8').replace("LAB/'VoiceService5'","LAB/'VoiceService6'")
test=test.replace("self.assertEqual(payload['text'],'先坐一会儿，好吗？')","self.assertEqual(payload['text'],'先坐一会儿，\\n好吗？')")
test=test.replace("self.assertNotIn('\\n',GptSovitsTts(TtsConfig()).payload('别着急，慢慢说就好。')['text'])", "self.assertNotIn('\\n',GptSovitsTts(TtsConfig()).payload('事情又不会趁你休息的时候跑掉，我们明天再说。')['text'])")
anchor='    def test_stable_spoken_style_is_added_without_changing_user_messages(self):'
addition='''    def test_short_lead_in_is_protected_for_the_installed_voice(self):
        payload=GptSovitsTts(TtsConfig()).payload('先坐一会儿吧，事情又不会趁你休息的时候跑掉。')
        self.assertEqual(payload['text'],'先坐一会儿吧，\\n事情又不会趁你休息的时候跑掉。')

'''
assert test.count(anchor)==1;test=test.replace(anchor,addition+anchor)
with (lab/'test_speech6.py').open('x',encoding='utf-8') as output:output.write(test)
helper=(lab/'VoiceRepair/launch_unified.py').read_text(encoding='utf-8').replace("SERVICE=DELIVERY/'VoiceService5'","SERVICE=DELIVERY/'VoiceService6'").replace('natural-phrases-v1','natural-phrases-v2')
with (lab/'VoiceRepair/launch_voice_final.py').open('x',encoding='utf-8') as output:output.write(helper)
check=(lab/'check_live_voice.py').read_text(encoding='utf-8').replace("LAB/'VoiceService5'","LAB/'VoiceService6'").replace("LAB/'LiveExamples'","LAB/'LiveFinal'").replace("LAB/'live-voice-check.json'","LAB/'live-final-check.json'")
with (lab/'check_live_final.py').open('x',encoding='utf-8') as output:output.write(check)
print(new)
