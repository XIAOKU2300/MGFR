from pathlib import Path
import difflib, hashlib, json, shutil

lab=Path(__file__).resolve().parent
base=lab.parent/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService'
service=lab/'VoiceService'
assert not service.exists()
changes={Path('app/text.py'):(lab/'Source/text.py').read_text(encoding='utf-8')}
def once(s,a,b):
    assert s.count(a)==1,a[:100]
    return s.replace(a,b)
p=Path('app/pipeline.py');s=(base/p).read_text(encoding='utf-8-sig')
s=once(s,'from .text import SentenceAccumulator','from .text import SentenceAccumulator, normalize_for_speech')
s=once(s,'accumulator = SentenceAccumulator(max_chars=session.config.tts.max_sentence_chars)','accumulator = SentenceAccumulator(max_chars=64, min_chars=12)')
s=once(s,'        pending = ""\n','')
start=s.index('                for sentence in accumulator.push(delta):')
end=s.index('            metrics = getattr(session.engines.llm, "metrics", None)',start)
s=s[:start]+'''                for sentence in accumulator.push(delta):
                    await queue.put(sentence)
            if not session.is_current(round_):
                return
            for sentence in accumulator.flush():
                await queue.put(sentence)
'''+s[end:]
s=once(s,'    sentence = sentence.strip()','    sentence = normalize_for_speech(sentence)');changes[p]=s
p=Path('app/engines/tts_gptsovits.py');s=(base/p).read_text(encoding='utf-8-sig')
s=once(s,'from ..config import TtsConfig','from ..config import TtsConfig\nfrom ..text import normalize_for_speech')
s=once(s,'            "text": text,','            "text": normalize_for_speech(text),')
s=once(s,'''            "streaming_mode": 2,
            "fragment_interval": .08,
            "overlap_length": 4,
            "min_chunk_length": 16,''','''            "streaming_mode": 1 if self.cfg.streaming_mode else 0,
            "text_split_method": "cut0",
            "fragment_interval": .10,
            "speed_factor": 1.0,
            "batch_size": 1,
            "split_bucket": False,''')
s=once(s,'        epoch = self._epoch\n        async with self._sem:', '''        text = normalize_for_speech(text)
        if not text:
            return
        epoch = self._epoch
        async with self._sem:''');changes[p]=s
p=Path('app/engines/llm_openai.py');s=(base/p).read_text(encoding='utf-8-sig')
s=once(s,'from ..config import LlmConfig','from ..config import LlmConfig\nfrom ..speech_style import SPOKEN_STYLE')
s=once(s,"self.cfg=cfg;self.system_prompt=cfg.load_system_prompt();self._client=None", "self.cfg=cfg;self.system_prompt=(cfg.load_system_prompt()+'\\n\\n'+SPOKEN_STYLE).strip();self._client=None");changes[p]=s
p=Path('app/main.py');s=(base/p).read_text(encoding='utf-8-sig')
s=once(s,'            "protocolVersion": protocol.PROTOCOL_VERSION,','            "protocolVersion": protocol.PROTOCOL_VERSION,\n            "speechRevision": "natural-phrases-v1",');changes[p]=s

def ignore(directory,names):
    return [n for n in names if n=='__pycache__' or (Path(directory)/n).relative_to(base) in changes]
shutil.copytree(base/'app',service/'app',ignore=ignore)
for p,s in changes.items():
    with (service/p).open('x',encoding='utf-8',newline='\n') as output:output.write(s)
shutil.copyfile(lab/'Source/speech_style.py',service/'app/speech_style.py')
patch=[]
for p,s in changes.items():
    patch+=difflib.unified_diff((base/p).read_text(encoding='utf-8-sig').splitlines(True),s.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix())
with (lab/'speech-adaptation.patch').open('x',encoding='utf-8') as output:output.writelines(patch)
with (lab/'base-hashes.json').open('x',encoding='utf-8') as output:
    json.dump({p.as_posix():hashlib.sha256((base/p).read_bytes()).hexdigest() for p in changes},output,indent=2)
print(service)
