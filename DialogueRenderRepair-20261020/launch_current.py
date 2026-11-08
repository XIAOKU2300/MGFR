"""Start the corrected player and a separately identified voice worker without resetting services."""
import argparse
import datetime
import json
import os
from pathlib import Path
import runpy
import socket
import subprocess
import sys
import threading
import time
from urllib.request import build_opener, ProxyHandler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RELEASE = HERE / 'Current'
PLAYER = RELEASE / 'Player/MGFR.exe'
PYTHON = ROOT / 'dialogue-service/.venv/Scripts/python.exe'
VOICE_PORT = 8776
ACTION_PORT = 18769
REVISION = 'structured-history-natural-clauses-v4'
OPENER = build_opener(ProxyHandler({}))

def get_json(url):
    with OPENER.open(url, timeout=2) as response:
        return json.load(response)

def read_health():
    try:
        return get_json(f'http://127.0.0.1:{VOICE_PORT}/health')
    except OSError:
        return None

def verify(health):
    expected = {'vad': 'silero', 'asr': 'sensevoice', 'llm': 'openai', 'tts': 'gptsovits'}
    if not health or health.get('status') != 'ok' or health.get('engines') != expected or health.get('avatarRevision') != REVISION:
        raise RuntimeError('Repair voice identity/health mismatch; existing services preserved')
    config = ROOT / 'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml'
    if Path(health.get('configSource', '')).resolve() != config.resolve():
        raise RuntimeError('Repair configuration source mismatch')

def worker():
    service = ROOT / 'SpeechNatural-20261019/VoiceService10'
    sys.path[:0] = [str(service), str(RELEASE / 'Voice')]
    sys.dont_write_bytecode = True
    namespace = runpy.run_path(str(service / 'voice_server.py'), run_name='repair_original_private_bootstrap')
    app = namespace['namespace']['app']
    from install_voice_v4 import install
    install(app, f'http://127.0.0.1:{ACTION_PORT}')
    sys.path.append(str(ROOT / 'SiLLMBridge-20261020'))
    from main_bridge_final import make_server
    catalog = json.loads((ROOT / 'SiLLMBridge-20261020/MainData/catalog.json').read_text(encoding='utf-8'))
    bridge = make_server(catalog, ACTION_PORT)
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=VOICE_PORT, log_level='warning', access_log=False)
    finally:
        bridge.shutdown()
        bridge.server_close()
        thread.join(timeout=3)

def ensure_worker():
    health = read_health()
    if health:
        verify(health)
        return
    # Refuse occupied ports instead of stopping their owners.
    for port in [VOICE_PORT, ACTION_PORT]:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', port))
    logs = HERE / 'Logs'
    logs.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    log = logs / ('voice-' + stamp + '.log')
    env = os.environ.copy()
    env.update({'PYTHONUTF8': '1', 'NO_PROXY': '127.0.0.1,localhost'})
    with log.open('xb') as stream:
        child = subprocess.Popen([str(PYTHON), '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--worker'], cwd=ROOT, env=env, stdout=stream, stderr=stream, creationflags=subprocess.CREATE_NO_WINDOW)
    with (logs / ('voice-start-' + stamp + '.json')).open('x', encoding='utf-8') as stream:
        json.dump({'pid': child.pid, 'voicePort': VOICE_PORT, 'actionPort': ACTION_PORT, 'log': str(log)}, stream, indent=2)
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        health = read_health()
        if health:
            verify(health)
            return
        if child.poll() is not None:
            raise RuntimeError('New repair voice worker exited; see its diagnostic log')
        time.sleep(.2)
    raise RuntimeError('Repair worker startup timed out; old services preserved')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--service-only', action='store_true')
    parser.add_argument('--desktop', action='store_true')
    args = parser.parse_args()
    if args.worker:
        return worker()
    if args.check:
        health = read_health()
        if health:
            verify(health)
        print(json.dumps({'playerExists': PLAYER.is_file(), 'repairVoiceHealthy': bool(health), 'revision': health.get('avatarRevision') if health else None, 'voicePort': VOICE_PORT, 'actionPort': ACTION_PORT, 'mode': 'read-only preflight'}, indent=2))
        return
    ensure_worker()
    get_json('http://127.0.0.1:9880/voice_info')
    actions = get_json(f'http://127.0.0.1:{ACTION_PORT}/v1/catalog')
    if sum(x.get('callable', True) for x in actions.get('actions', [])) != 19:
        raise RuntimeError('Repair action catalog mismatch')
    if args.service_only:
        print('REPAIR_VOICE_READY', REVISION, flush=True)
        return
    logs = HERE / 'Logs'
    logs.mkdir(exist_ok=True)
    log = logs / ('player-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.log')
    command = [str(PLAYER), '-mgfr-service-url', f'ws://127.0.0.1:{VOICE_PORT}/ws', '-mgfr-action-port', str(ACTION_PORT), '-mgfr-structured-voice', '-mgfr-avatar-data', str(ROOT / 'SiLLMBridge-20261020/MainData'), '-mgfr-skins', '-mgfr-skin', 'swimsuit', '-mgfr-zmd', '-mgfr-mr-clean-edge', '-mgfr-wardrobe', '-mgfr-shoes', '-logFile', str(log)]
    if args.desktop:
        command.append('-mgfr-noxr')
    subprocess.Popen(command, cwd=PLAYER.parent)
    print('Corrected dialogue and MR-material player started.', flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Repair startup failed: ' + type(error).__name__ + '. Existing services were preserved.', file=sys.stderr)
        raise SystemExit(1)
