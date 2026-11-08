from pathlib import Path
import json
import subprocess
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT.parent / 'dialogue-service/.venv/Scripts/python.exe'
OPENER = build_opener(ProxyHandler({}))


def main():
    output = ROOT / 'main-network-review-v2'
    output.mkdir(exist_ok=False)
    children = []
    handles = []
    try:
        for script, port, label in [(ROOT / 'main_bridge_final.py', 18766, 'bridge'), (ROOT / 'main_test_voice_server.py', 8775, 'test-voice')]:
            try:
                with OPENER.open('http://127.0.0.1:' + str(port) + '/health', timeout=.3):
                    raise RuntimeError('Test port already occupied; no process was stopped')
            except OSError:
                pass
            stream = (output / (label + '.log')).open('xb')
            handles.append(stream)
            child = subprocess.Popen([str(PYTHON), '-X', 'utf8', str(script)], cwd=ROOT, stdout=stream, stderr=stream,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            children.append(child)
            for _ in range(100):
                try:
                    with OPENER.open('http://127.0.0.1:' + str(port) + '/health', timeout=.2) as response:
                        if json.load(response).get('ok', label == 'test-voice'):
                            break
                except OSError:
                    time.sleep(.1)
                if child.poll() is not None:
                    raise RuntimeError('Local fixture startup failed: ' + label)
            else:
                raise RuntimeError('Local fixture timeout')
        player = ROOT / 'MainPlayer-StructuredVoice/MGFR.exe'
        args = [str(player), '-batchmode', '-mgfr-structured-voice', '-mgfr-avatar-data', str(ROOT / 'MainData'),
                '-mgfr-actions-network-review', '-mgfr-actions-network-out', str(output / 'result.json'),
                '-mgfr-service-url', 'ws://127.0.0.1:8775/ws', '-mgfr-noxr', '-mgfr-skins', '-mgfr-skin', 'swimsuit',
                '-mgfr-zmd', '-mgfr-wardrobe', '-mgfr-shoes', '-logFile', str(output / 'main.log')]
        with (output / 'startup.log').open('xb') as stream:
            child = subprocess.Popen(args, cwd=player.parent, stdout=stream, stderr=stream, creationflags=subprocess.CREATE_NO_WINDOW)
            children.append(child)
            code = child.wait(timeout=55)
        result = json.loads((output / 'result.json').read_text(encoding='utf-8-sig'))
        print(json.dumps(result, ensure_ascii=False))
        if code != 0 or not result['pass']:
            raise RuntimeError('Main voice/action integration check failed')
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        for stream in handles:
            stream.close()


if __name__ == '__main__':
    main()
