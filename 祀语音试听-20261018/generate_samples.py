"""Compare both voices through real HTTP synthesis, then restore default 00."""
import io
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('F:/GPT-SoVITS/GPT-SoVITS-v2pro-20250604-nvidia50/GPT-SoVITS-v2pro-20250604-nvidia50')
BASE = 'http://127.0.0.1:9880'
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
MANIFEST = json.loads((ROOT / 'si_voice_20261018/manifest.json').read_text(encoding='utf-8'))
TEXTS = [
    ('01_问候', '你终于来了。我是祀，今天就由我陪着你，慢慢来吧。'),
    ('02_安慰', '别着急，先坐下来休息一会儿。有什么烦心事，可以慢慢说给我听。'),
    ('03_询问', '嗯？你一直看着我做什么？难道，是有什么话想对我说吗？'),
]

def request(path, data=None):
    body = None if data is None else json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE + path, data=body, headers={'Content-Type': 'application/json'})
    try:
        with HTTP.open(req, timeout=180) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError('TTS HTTP ' + str(exc.code) + ': ' + exc.read().decode('utf-8', 'replace')[:1000]) from None

def switch(key):
    model = MANIFEST['models'][key]
    for endpoint, field in [('/set_sovits_weights', 'sovits'), ('/set_gpt_weights', 'gpt')]:
        result = json.loads(request(endpoint + '?' + urllib.parse.urlencode({'weights_path': model[field]})))
        assert result['message'] == 'success', result
    state = json.loads(request('/voice_info'))
    assert Path(state['gpt']) == Path(model['gpt']) and Path(state['sovits']) == Path(model['sovits'])
    print('LOADED', key, state['version'], flush=True)

def main():
    for attempt in range(60):
        try:
            print('READY', request('/voice_info').decode('utf-8')[:180], flush=True)
            break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    else:
        raise RuntimeError('API failed to become ready')
    outputs = []
    try:
        for key in ['00', '1']:
            switch(key)
            model = MANIFEST['models'][key]
            for label, text in TEXTS:
                output = HERE / ('祀' + key + '_' + label + '.wav')
                if output.exists():
                    raise FileExistsError('Refusing to overwrite ' + str(output))
                payload = {'text': text, 'text_lang': 'zh', 'ref_audio_path': model['ref_audio'],
                           'prompt_text': model['prompt_text'], 'prompt_lang': 'zh',
                           'top_k': 15, 'top_p': 1.0, 'temperature': 0.8, 'speed_factor': 1.0,
                           'text_split_method': 'cut5', 'batch_size': 1, 'split_bucket': True,
                           'seed': 20261018, 'media_type': 'wav', 'streaming_mode': False,
                           'parallel_infer': True, 'repetition_penalty': 1.35}
                started = time.perf_counter()
                audio = request('/tts', payload)
                elapsed = time.perf_counter() - started
                with wave.open(io.BytesIO(audio), 'rb') as wav:
                    assert wav.getnchannels() == 1 and wav.getsampwidth() == 2
                    rate = wav.getframerate()
                    pcm = array('h', wav.readframes(wav.getnframes()))
                    duration = wav.getnframes() / rate
                peak = max(abs(x) for x in pcm)
                rms = math.sqrt(sum(float(x) * x for x in pcm) / len(pcm))
                assert duration > 0.5 and peak > 100 and rms > 10, 'Empty or silent audio'
                with output.open('xb') as stream:
                    stream.write(audio)
                item = {'variant': key, 'text': text, 'path': str(output), 'sample_rate': rate,
                        'duration_s': round(duration, 3), 'generation_s': round(elapsed, 3),
                        'peak': peak, 'rms': round(rms, 1), 'parameters': payload}
                outputs.append(item)
                print('GENERATED', output.name, 'duration', round(duration, 2), 'seconds; synthesis', round(elapsed, 2), flush=True)
    finally:
        switch('00')
    with (HERE / 'samples.json').open('x', encoding='utf-8') as stream:
        json.dump({'model_name': '祀的语音', 'default_variant': '00', 'samples': outputs}, stream, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
