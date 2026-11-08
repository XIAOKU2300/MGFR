from pathlib import Path
import shutil
LAB=Path(__file__).resolve().parent
source=LAB/'VoiceService9';target=LAB/'VoiceService10'
assert not target.exists()
shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','*.log'))
def change(relative,old,new):
    path=target/relative;text=path.read_text(encoding='utf-8');assert old in text,relative
    path.write_text(text.replace(old,new),encoding='utf-8')
change('app/engines/tts_gptsovits.py',
    '                for attempt, seed in enumerate((None, 0, 7, 42)):',
    '''                # Match the installed text front end's onset-padding remedy
                # only after readback rejects the original pronunciation. The
                # added stop is punctuation, never an extra spoken word.
                attempts = (None, {"seed": 0},
                            {"seed": 0, "text": "。" + phrase},
                            {"seed": 7, "text": "。" + phrase})
                for attempt, options in enumerate(attempts):''')
change('app/engines/tts_gptsovits.py','                    options = None if seed is None else {"seed": seed}\n','')
change('app/main.py','natural-phrases-v5','natural-phrases-v6')
change('app/speech_verify.py',"    text = re.sub('(['+_CN+']+)(?:点(['+_CN+']+))?',",
    '''    # Clock minutes use integer notation; do not consume 三十 as a decimal.
    text = re.sub('(['+_CN+']+)点(['+_CN+']+)分',
        lambda m:str(_integer(m[1]))+'点'+str(_integer(m[2]))+'分',text)
    text = re.sub('(['+_CN+']+)(?:点(['+_CN+']+))?',''')
change('app/speech_verify.py','    original = text\n','')
helper=(LAB/'VoiceRepair/launch_voice_v5.py').read_text(encoding='utf-8').replace('VoiceService9','VoiceService10').replace('natural-phrases-v5','natural-phrases-v6')
(LAB/'VoiceRepair/launch_voice_v6.py').write_text(helper,encoding='utf-8')
tests=(LAB/'test_speech9.py').read_text(encoding='utf-8').replace('VoiceService9','VoiceService10')
tests=tests.replace('class FakeLlm:', '''class ClockCompletenessTests(unittest.TestCase):
    def test_written_clock_minutes_match_half_hour_readback(self):
        from app.speech_verify import speech_completeness
        self.assertGreaterEqual(speech_completeness('现在是十二点三十分。','现在是12点半。'),.72)
        self.assertLess(speech_completeness('现在是十二点三十分。','现在是12点20分。'),.72)


class FakeLlm:''')
(LAB/'test_speech10.py').write_text(tests,encoding='utf-8')
guard=(LAB/'test_quality_guards.py').read_text(encoding='utf-8').replace('VoiceService9','VoiceService10')
(LAB/'test_quality_guards10.py').write_text(guard,encoding='utf-8')
live=(LAB/'check_live_checked.py').read_text(encoding='utf-8').replace('VoiceService9','VoiceService10').replace('LiveChecked','LiveAccepted').replace('live-checked-report','live-accepted-report')
(LAB/'check_live_accepted.py').write_text(live,encoding='utf-8')
verify=(LAB/'verify_checked_voice.py').read_text(encoding='utf-8').replace('VoiceService9','VoiceService10').replace('LiveChecked','LiveAccepted').replace('live-checked-report','live-accepted-report').replace('checked-validation','accepted-validation').replace("'unitTestsPassed':20","'unitTestsPassed':24")
(LAB/'verify_accepted_voice.py').write_text(verify,encoding='utf-8')
print('Created candidate 10; all prior candidates and original files preserved.')
