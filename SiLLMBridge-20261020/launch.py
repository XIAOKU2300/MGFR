"""Start this local bridge and its character window; stop owned server on exit."""
from pathlib import Path
import datetime
import json
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent


def main():
    opener = build_opener(ProxyHandler({}))
    server = None
    log = None
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    try:
        try:
            with opener.open('http://127.0.0.1:18766/health', timeout=.5) as response:
                existing = json.load(response)
            if existing != {'ok': True, 'version': 1}:
                raise RuntimeError('Port 18766 belongs to another service')
        except OSError:
            logs = ROOT / 'logs'
            logs.mkdir(exist_ok=True)
            log = (logs / ('server-' + stamp + '.log')).open('xb')
            server = subprocess.Popen([sys.executable, '-X', 'utf8', str(ROOT / 'bridge_server.py')],
                                      cwd=ROOT, stdout=log, stderr=log,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError('Bridge startup failed; see new server log')
                try:
                    with opener.open('http://127.0.0.1:18766/health', timeout=.2) as response:
                        if json.load(response).get('ok'):
                            break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Local bridge startup timed out')
        player = ROOT / 'Player-v1/SiLLMPlayer.exe'
        subprocess.run([str(player)], cwd=player.parent, check=False)
    except (OSError, RuntimeError) as exc:
        print('Startup error:', exc)
        return 1
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            server.wait(timeout=5)
        if log:
            log.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
