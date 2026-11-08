"""Back up the project config and prepare a reviewable replacement, without applying it."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = Path('H:/MGFR/dialogue-service/config.toml')
ROOT = Path('F:/GPT-SoVITS/GPT-SoVITS-v2pro-20250604-nvidia50/GPT-SoVITS-v2pro-20250604-nvidia50')
manifest = json.loads((ROOT / 'si_voice_20261018/manifest.json').read_text(encoding='utf-8'))
voice = manifest['models']['00']
original = TARGET.read_bytes()
text = original.decode('utf-8')
start = text.index('[tts]')
end = text.index('[session]', start)
replacement = '''[tts]
# 祀的语音: v2ProPlus, variant 00. The backend exposes this name at /voice_info.
model_name = "祀的语音"
base_url = "http://127.0.0.1:9880"
ref_audio = REF_AUDIO
prompt_text = PROMPT_TEXT
prompt_language = "zh"
text_language = "zh"
streaming_mode = true
media_type = ""
max_concurrent = 1
max_sentence_chars = 40
request_timeout_s = 120

'''.replace('REF_AUDIO', json.dumps(voice['ref_audio'].replace('\\', '/'), ensure_ascii=False)).replace(
    'PROMPT_TEXT', json.dumps(voice['prompt_text'], ensure_ascii=False))
candidate = text[:start] + replacement + text[end:]
with (HERE / 'MGFR-config.before.toml').open('xb') as stream:
    stream.write(original)
with (HERE / 'MGFR-config.preview.toml').open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(candidate)
review = {'target': str(TARGET), 'original_sha256': hashlib.sha256(original).hexdigest(),
          'candidate': str(HERE / 'MGFR-config.preview.toml'), 'backup': str(HERE / 'MGFR-config.before.toml'),
          'model_name': '祀的语音', 'default_variant': '00'}
with (HERE / 'config-review.json').open('x', encoding='utf-8') as stream:
    json.dump(review, stream, ensure_ascii=False, indent=2)
print('Prepared candidate and byte-identical backup. Original config has not been changed.')
