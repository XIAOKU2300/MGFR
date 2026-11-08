"""Launch the existing GPT-SoVITS API with a separate, read-only voice config."""
import argparse
import json
import os
import runpy
import socket
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--model', choices=['00', '1'], default='00')
parser.add_argument('--port', type=int, default=9880)
args = parser.parse_args()
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
config_path = HERE / ('tts_si_' + args.model + '.yaml')
with socket.socket() as check:
    check.bind(('127.0.0.1', args.port))
os.chdir(ROOT)
sys.path[:0] = [str(ROOT), str(ROOT / 'GPT_SoVITS')]
os.environ['PATH'] = str(ROOT / 'runtime') + os.pathsep + os.environ['PATH']
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

from GPT_SoVITS.TTS_infer_pack.TTS import TTS_Config

def keep_configs_readonly(self, configs_path=None):
    # Upstream normally persists weights on every load. This launcher deliberately
    # keeps all on-disk configs intact; /set_* only changes this running instance.
    return None

TTS_Config.save_configs = keep_configs_readonly
sys.argv = ['api_v2.py', '-c', str(config_path), '-a', '127.0.0.1', '-p', str(args.port)]
api = runpy.run_path(str(ROOT / 'api_v2.py'), run_name='si_voice_api')
app = api['APP']
app.title = '祀的语音'
manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))

@app.get('/voice_info')
async def voice_info():
    cfg = api['tts_pipeline'].configs
    return {'model_name': '祀的语音', 'version': cfg.version,
            'gpt': str(cfg.t2s_weights_path), 'sovits': str(cfg.vits_weights_path),
            'variants': manifest['models']}

import uvicorn
uvicorn.run(app, host='127.0.0.1', port=args.port, workers=1)
