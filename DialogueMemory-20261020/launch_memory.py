"""Current player plus isolated memory; retain original private voice configuration."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import runpy
import secrets
import socket
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from urllib.request import ProxyHandler, build_opener

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = HERE / 'src_v3'
RELEASE = ROOT / 'DialogueRenderRepair-20261020/Final-v3'
PLAYER = RELEASE / 'Player/MGFR.exe'
DELIVERY = HERE
VOICE_PYTHON = ROOT / 'dialogue-service/.venv/Scripts/python.exe'
MEMORY_PYTHON = HERE / '.venv/Scripts/python.exe'
VOICE_PORT, ACTION_PORT, MEMORY_PORT = 8779, 18772, 18780
VOICE_URL = f'http://127.0.0.1:{VOICE_PORT}'
MEMORY_URL = f'http://127.0.0.1:{MEMORY_PORT}'
REVISION = 'mem0-role-memory-v1'
OPENER = build_opener(ProxyHandler({}))


def health(url):
    try:
        with OPENER.open(url + '/health', timeout=2) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def paths():
    return Path(os.environ.get('MGFR_MEMORY_DATA', str(HERE / 'Data')))


def build_identity():
    digest = hashlib.sha256()
    for path in [Path(__file__).resolve(), *sorted(SOURCE.rglob('*.py')), *sorted((RELEASE / 'Voice').glob('*.py'))]:
        digest.update(str(path.relative_to(ROOT)).encode('utf-8'))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def environment():
    data = paths()
    data.mkdir(parents=True, exist_ok=True)
    token_file = data / 'local-auth.token'
    if not token_file.exists():
        with token_file.open('x', encoding='ascii') as stream:
            stream.write(secrets.token_urlsafe(40))
    token = token_file.read_text(encoding='ascii').strip()
    if len(token) < 32:
        raise RuntimeError('Local memory token is invalid')
    env = os.environ.copy()
    env.update({
        'MGFR_MEMORY_DATA': str(data), 'MGFR_MEMORY_MODELS': str(HERE / 'Models'),
        'MGFR_MEMORY_MODEL_PATH': str(HERE / 'Models/bge-small-zh-manual-v1'),
        'MGFR_MEMORY_TOKEN': token, 'MGFR_MEMORY_EXTRACT_URL': VOICE_URL + '/mgfr-memory/extract',
        'MEM0_DIR': str(data / 'engine'), 'MEM0_TELEMETRY': 'false',
        'HF_HOME': str(HERE / 'Models/hf-cache'), 'HF_HUB_OFFLINE': '1',
        'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HUB_DISABLE_SYMLINKS_WARNING': '1',
        'TOKENIZERS_PARALLELISM': 'false', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONUTF8': '1', 'NO_PROXY': '127.0.0.1,localhost',
        'MGFR_MEMORY_BUILD': build_identity(),
        'MGFR_MEMORY_STORE': hashlib.sha256(str(data.resolve()).encode('utf-8')).hexdigest()[:16],
        'MGFR_MEMORY_WARMUP': '1',
    })
    return env


def voice_worker():
    service = ROOT / 'SpeechNatural-20261019/VoiceService10'
    repair = RELEASE / 'Voice'
    sys.path[:0] = [str(service), str(repair), str(SOURCE)]
    sys.dont_write_bytecode = True
    namespace = runpy.run_path(str(service / 'voice_server.py'), run_name='mgfr_memory_original_bootstrap')
    app = namespace['namespace']['app']
    from install_voice_v4 import install as install_original_voice
    install_original_voice(app, f'http://127.0.0.1:{ACTION_PORT}')
    from lore_speech import install as install_lore_readback
    install_lore_readback()
    from voice_memory import install
    install(app, url=MEMORY_URL, token=os.environ['MGFR_MEMORY_TOKEN'])
    app.state.memory_build = os.environ['MGFR_MEMORY_BUILD']
    app.state.memory_store = os.environ['MGFR_MEMORY_STORE']
    from interaction_context import install as install_interactions
    install_interactions(app)
    sys.path.append(str(ROOT / 'SiLLMBridge-20261020'))
    from main_bridge_final import make_server
    catalog = json.loads((ROOT / 'SiLLMBridge-20261020/MainData/catalog.json').read_text(encoding='utf-8'))
    server = make_server(catalog, ACTION_PORT)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name='memory-candidate-avatar-interface')
    thread.start()
    try:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=VOICE_PORT, log_level='warning', access_log=False)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def memory_worker():
    sys.path.insert(0, str(SOURCE))
    import logging
    logging.getLogger('mem0').setLevel(logging.CRITICAL)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    from loguru import logger
    logger.remove()
    import uvicorn
    from mgfr_memory.service import create_app
    app = create_app(knowledge=SOURCE / 'knowledge.zh.json')
    uvicorn.run(app, host='127.0.0.1', port=MEMORY_PORT, log_level='warning', access_log=False)


def spawn(kind, python, args, env):
    logs = HERE / 'Logs'
    logs.mkdir(exist_ok=True)
    path = logs / (kind + '-' + uuid.uuid4().hex + '.log')
    with path.open('xb') as stream:
        child = subprocess.Popen([str(python), '-B', '-X', 'utf8', str(Path(__file__).resolve()), *args],
                                 cwd=ROOT, env=env, stdout=stream, stderr=stream,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
    with (logs / (kind + '-start-' + uuid.uuid4().hex + '.json')).open('x', encoding='utf-8') as stream:
        json.dump({'pid': child.pid, 'kind': kind, 'build': env['MGFR_MEMORY_BUILD'], 'store': env['MGFR_MEMORY_STORE'], 'log': str(path)}, stream, indent=2)
    return child


def ensure_service():
    env = environment()
    for kind, url, port, python, args, field in [
        ('memory', MEMORY_URL, MEMORY_PORT, MEMORY_PYTHON, ['--memory-worker'], 'revision'),
        ('voice', VOICE_URL, VOICE_PORT, VOICE_PYTHON, ['--voice-worker'], 'memoryRevision'),
    ]:
        current = health(url)
        if current:
            if current.get(field) != REVISION or current.get('build' if kind == 'memory' else 'memoryBuild') != env['MGFR_MEMORY_BUILD'] or current.get('store' if kind == 'memory' else 'memoryStore') != env['MGFR_MEMORY_STORE']:
                raise RuntimeError('Candidate port belongs to another service; preserved')
            continue
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', port))
        if kind == 'voice':
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', ACTION_PORT))
        child_env = env.copy()
        if kind == 'memory':
            for key in ('MGFR_LLM_API_KEY', 'OPENAI_API_KEY', 'DEEPSEEK_API_KEY'):
                child_env.pop(key, None)
        child = spawn(kind, python, args, child_env)
        if kind == 'voice':
            print('Preparing the existing voice model; startup audio is not played.', flush=True)
        deadline = time.monotonic() + (130 if kind == 'voice' else 40)
        while time.monotonic() < deadline:
            current = health(url)
            if current and current.get(field) == REVISION:
                if kind == 'memory' and not current.get('ready'):
                    raise RuntimeError('Memory candidate is not ready')
                if kind == 'voice' and current.get('status') != 'ok':
                    raise RuntimeError('Original voice engines are not ready')
                if current.get('build' if kind == 'memory' else 'memoryBuild') != env['MGFR_MEMORY_BUILD']:
                    raise RuntimeError('Service code identity mismatch; existing process preserved')
                break
            if child.poll() is not None:
                raise RuntimeError('Candidate worker exited; see its local diagnostic log')
            time.sleep(.2)
        else:
            raise RuntimeError('Candidate worker startup exceeded its deadline')
    return env


def ensure_existing_tts():
    try:
        with OPENER.open('http://127.0.0.1:9880/voice_info', timeout=2) as response:
            json.load(response)
        return
    except (OSError, ValueError):
        pass
    configuration = ROOT / 'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml'
    config = tomllib.loads(configuration.read_text(encoding='utf-8-sig'))
    reference = Path(config['tts']['ref_audio'])
    variant = {'ref_si_00.wav': '00', 'ref_si_1.wav': '1'}.get(reference.name)
    service = reference.parent / 'serve_si.py'
    runtime = service.parent.parent / 'runtime/python.exe'
    if variant is None or not service.is_file() or not runtime.is_file():
        raise RuntimeError('The configured original voice launcher could not be resolved')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 9880))
    env = os.environ.copy()
    env['PATH'] = str(runtime.parent) + os.pathsep + env['PATH']
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    logs = HERE / 'Logs'
    logs.mkdir(exist_ok=True)
    with (logs / ('original-tts-' + uuid.uuid4().hex + '.log')).open('xb') as stream:
        child = subprocess.Popen([str(runtime), '-I', '-B', '-X', 'utf8', str(service), '--model', variant, '--port', '9880'],
                                 cwd=service.parent.parent, env=env, stdout=stream, stderr=stream,
                                 creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
    # Only the TTS process created above receives this measured CPU budget.
    # Existing shared services are reused by the early health return, unchanged.
    spec = importlib.util.spec_from_file_location('mgfr_owned_tts_resource_policy', RELEASE / 'Voice/tts_resource_policy.py')
    resource_policy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resource_policy)
    resource_policy.configure_owned_tts(child)
    print('Starting the existing configured voice model.', flush=True)
    deadline = time.monotonic() + 70
    while time.monotonic() < deadline:
        try:
            with OPENER.open('http://127.0.0.1:9880/voice_info', timeout=2) as response:
                json.load(response)
            return
        except (OSError, ValueError):
            if child.poll() is not None:
                raise RuntimeError('The original voice model did not start') from None
            time.sleep(.25)
    raise RuntimeError('The original voice model startup exceeded its deadline')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice-worker', action='store_true')
    parser.add_argument('--memory-worker', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--service-only', action='store_true')
    parser.add_argument('--desktop', action='store_true')
    args = parser.parse_args()
    if args.voice_worker:
        return voice_worker()
    if args.memory_worker:
        return memory_worker()
    if args.check:
        print(json.dumps({'playerExists': PLAYER.is_file(), 'player': str(PLAYER), 'source': str(SOURCE), 'expectedBuild': build_identity(),
                          'memory': health(MEMORY_URL), 'voice': health(VOICE_URL),
                          'mode': 'read-only; no microphone or model request'}, ensure_ascii=False, indent=2))
        return
    ensure_existing_tts()
    ensure_service()
    if args.service_only:
        print('Memory candidate and original voice engines are ready.')
        return
    with OPENER.open('http://127.0.0.1:9880/voice_info', timeout=3) as response:
        json.load(response)
    logs = HERE / 'Logs'
    log = logs / ('player-' + uuid.uuid4().hex + '.log')
    command = [str(PLAYER), '-mgfr-service-url', f'ws://127.0.0.1:{VOICE_PORT}/ws',
               '-mgfr-action-port', str(ACTION_PORT), '-mgfr-structured-voice',
               '-mgfr-avatar-data', str(ROOT / 'SiLLMBridge-20261020/MainData'),
               '-mgfr-skins', '-mgfr-skin', 'swimsuit', '-mgfr-zmd', '-mgfr-mr-clean-edge',
               '-mgfr-wardrobe', '-mgfr-shoes', '-logFile', str(log)]
    command.append('-mgfr-dialogue-context')
    if args.desktop:
        command.append('-mgfr-noxr')
    subprocess.Popen(command, cwd=PLAYER.parent)
    print('Current player started with the candidate memory voice endpoint.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('MGFR memory candidate failed (' + type(error).__name__ + '); existing services were preserved.', file=sys.stderr)
        raise SystemExit(1)
