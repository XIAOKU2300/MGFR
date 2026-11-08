from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent
old=lab/'VoiceService3';new=lab/'VoiceService4'
assert not new.exists()
rel=Path('app/engines/tts_gptsovits.py')
s=(old/rel).read_text(encoding='utf-8')
a='from ..text import normalize_for_speech, prepare_tts_text'
assert s.count(a)==1;s=s.replace(a,a+'\nfrom ..speech_pcm import SpeechPcmSmoother')
a='            carry = bytearray()'
assert s.count(a)==1;s=s.replace(a,a+'\n            smoother = None')
a='                carry.extend(pcm)'
assert s.count(a)==1;s=s.replace(a,'''                if smoother is None:
                    smoother = SpeechPcmSmoother(parser.sample_rate, parser.channels)
                carry.extend(smoother.push(pcm))''')
a='            if carry and not cancel.is_set() and epoch == self._epoch:'
assert s.count(a)==1
s=s.replace(a,'''            if smoother is not None and not cancel.is_set() and epoch == self._epoch:
                carry.extend(smoother.flush())
            while len(carry) >= frame_bytes and not cancel.is_set() and epoch == self._epoch:
                out = bytes(carry[:frame_bytes]); del carry[:frame_bytes]
                yield AudioChunk(out, parser.sample_rate, parser.channels)
'''+a)
def ignore(directory,names):return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(old)==rel]
shutil.copytree(old,new,ignore=ignore)
with (new/rel).open('x',encoding='utf-8') as output:output.write(s)
shutil.copyfile(lab/'Source/speech_pcm.py',new/'app/speech_pcm.py')
test=(lab/'test_speech3.py').read_text(encoding='utf-8').replace("LAB/'VoiceService3'","LAB/'VoiceService4'")
anchor='class FakeLlm:'
addition='''class PcmPauseTests(unittest.TestCase):
    def test_voiced_samples_are_unchanged_and_excess_quiet_is_bounded(self):
        import numpy as np
        from app.speech_pcm import SpeechPcmSmoother
        rate=32000
        tone=(np.sin(np.arange(rate//5)*2*np.pi*240/rate)*6000).astype('<i2').tobytes()
        quiet=bytes(rate*2)
        original=quiet+tone+quiet+tone+quiet
        smoother=SpeechPcmSmoother(rate,1)
        actual=b''.join(smoother.push(original[i:i+317]) for i in range(0,len(original),317))+smoother.flush()
        self.assertEqual(actual.count(tone),2)
        self.assertLessEqual(len(actual)/(rate*2),.04+.2+.32+.2+.1+.01)
        self.assertGreater(smoother.dropped_bytes,0)

    def test_quiet_only_input_does_not_create_a_spoken_clip(self):
        from app.speech_pcm import SpeechPcmSmoother
        smoother=SpeechPcmSmoother(32000,1)
        self.assertEqual(smoother.push(bytes(64000))+smoother.flush(),b'')


'''
assert test.count(anchor)==1;test=test.replace(anchor,addition+anchor)
with (lab/'test_speech4.py').open('x',encoding='utf-8') as output:output.write(test)
print(new)
