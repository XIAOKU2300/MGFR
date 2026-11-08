"""Install two user-supplied voices; create files exclusively, never overwrite."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path('F:/GPT-SoVITS/GPT-SoVITS-v2pro-20250604-nvidia50/GPT-SoVITS-v2pro-20250604-nvidia50')
SOURCE = Path('H:/MGFR/祀语音/祀语音')
HERE = Path(__file__).resolve().parent
PACKAGE = ROOT / 'si_voice_20261018'
MODELS = {
    '00': {'folder': '祀00', 'gpt': '祀0-e15.ckpt', 'sovits': '祀0_e8_s168.pth',
           'ref': '祀0/祀合集-cut_vocals_karaoke.wav_0000192640_0000361600.wav',
           'prompt': '这个主意真够笨的，有不该亮起的灯，才有不该显形的影子。'},
    '1': {'folder': '祀1', 'gpt': '祀1-e15.ckpt', 'sovits': '祀1_e8_s248.pth',
          'ref': '祀1/祀语音-cut.wav_0000000000_0000137280.wav',
          'prompt': '我们在等什么？该从哪个地方起笔？'},
}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value)

def copy_new(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst)
    assert sha(source) == sha(target), 'Copy hash mismatch'

def main():
    plan = [(HERE / 'serve_si.py', PACKAGE / 'serve_si.py')]
    manifest = {'model_name': '祀的语音', 'version': 'v2ProPlus', 'default_variant': '00', 'models': {}}
    for key, m in MODELS.items():
        src = SOURCE / m['folder']
        gpt = ROOT / 'GPT_weights_v2ProPlus' / ('祀的语音-' + key + '-e15.ckpt')
        sovits = ROOT / 'SoVITS_weights_v2ProPlus' / ('祀的语音-' + key + '_e8.pth')
        ref = PACKAGE / ('ref_si_' + key + '.wav')
        plan += [(src / m['gpt'], gpt), (src / m['sovits'], sovits), (src / m['ref'], ref)]
        manifest['models'][key] = {'gpt': str(gpt), 'sovits': str(sovits), 'ref_audio': str(ref),
                                   'prompt_text': m['prompt'], 'prompt_language': 'zh', 'text_language': 'zh'}
    new_paths = [target for _, target in plan] + [PACKAGE / 'manifest.json']
    for key in MODELS:
        new_paths += [PACKAGE / ('tts_si_' + key + '.yaml')]
    for label in ['启动祀的语音.bat', '启动祀的语音-版本1.bat']:
        new_paths += [Path('F:/GPT-SoVITS') / label]
    assert all(source.is_file() for source, _ in plan), 'Missing source'
    existing = [str(path) for path in new_paths if path.exists()]
    if existing:
        raise FileExistsError('Refusing to overwrite: ' + repr(existing))
    for source, target in plan:
        copy_new(source, target)
        print('VERIFIED', target, flush=True)
    for key, m in manifest['models'].items():
        # JSON strings are valid YAML strings, including paths and Chinese names.
        values = {'device': 'cuda', 'is_half': True, 'version': 'v2ProPlus',
                  't2s_weights_path': m['gpt'].replace('\\', '/'),
                  'vits_weights_path': m['sovits'].replace('\\', '/'),
                  'bert_base_path': 'GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large',
                  'cnhuhbert_base_path': 'GPT_SoVITS/pretrained_models/chinese-hubert-base'}
        yaml_text = '# 祀的语音 / variant ' + key + '\ncustom:\n'
        for k, v in values.items():
            yaml_text += '  ' + k + ': ' + json.dumps(v, ensure_ascii=False) + '\n'
        write_new(PACKAGE / ('tts_si_' + key + '.yaml'), yaml_text)
        m['gpt_sha256'] = sha(Path(m['gpt']))
        m['sovits_sha256'] = sha(Path(m['sovits']))
    write_new(PACKAGE / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    for key, label in [('00', '启动祀的语音.bat'), ('1', '启动祀的语音-版本1.bat')]:
        # ASCII-only launcher to avoid cmd.exe codepage problems.
        launcher = '@echo off\r\ncd /d "' + str(ROOT) + '"\r\n'
        launcher += 'set "PATH=%CD%\\runtime;%PATH%"\r\n'
        launcher += 'runtime\\python.exe -I -B -X utf8 si_voice_20261018\\serve_si.py --model ' + key + ' --port 9880\r\npause\r\n'
        write_new(Path('F:/GPT-SoVITS') / label, launcher)
    print('Installed two v2ProPlus voices; default = 00', flush=True)

if __name__ == '__main__':
    main()
