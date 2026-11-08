"""Launch the real MGFR main project with JSON-first voice and authored gestures."""
from pathlib import Path
import datetime
import json
import os
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT.parent / 'dialogue-service/.venv/Scripts/python.exe'
OPENER = build_opener(ProxyHandler({}))


def get(path, timeout=1):
    try:
        with OPENER.open(path, timeout=timeout) as response:
            return json.load(response)
    except OSError:
        return None


def main():
    owned = []
    logs = []
    folder = ROOT / 'main-logs'
    folder.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')

    def start(script, label):
        log = (folder / (label + '-' + stamp + '.log')).open('xb')
        logs.append(log)
        env = os.environ.copy()
        env['PYTHONUTF8'] = '1'
        env['NO_PROXY'] = '127.0.0.1,localhost'
        process = subprocess.Popen([str(PYTHON), '-X', 'utf8', str(script)], cwd=script.parent,
                                   env=env, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        owned.append(process)
        return process

    try:
        print('正在启动主项目的动作与情绪接口...', flush=True)
        catalog = get('http://127.0.0.1:18766/v1/catalog')
        if catalog is None:
            child = start(ROOT / 'main_bridge_v2.py', 'actions')
            for _ in range(60):
                catalog = get('http://127.0.0.1:18766/v1/catalog', .3)
                if catalog:
                    break
                if child.poll() is not None:
                    raise RuntimeError('动作接口启动失败，请查看新日志。')
                time.sleep(.1)
        if not catalog or catalog.get('target') != 'MGFR main project existing character':
            raise RuntimeError('18766端口属于其他程序，未停止它。')
        revision = get('http://127.0.0.1:8774/avatar-health')
        if revision is None:
            print('正在加载原有ASR、LLM配置和GPT-SoVITS语音服务...', flush=True)
            child = start(ROOT / 'MainVoice-v1/voice_actions_server.py', 'voice')
            for _ in range(480):
                revision = get('http://127.0.0.1:8774/avatar-health', .5)
                if revision:
                    break
                if child.poll() is not None:
                    raise RuntimeError('结构化语音服务启动失败，请查看新日志。')
                time.sleep(.25)
        if not revision or revision.get('revision') != 'json-emotion-actions-v1':
            raise RuntimeError('8774端口未提供此版语音服务，未停止现有进程。')
        if get('http://127.0.0.1:9880/voice_info', 4) is None:
            raise RuntimeError('原有GPT-SoVITS语音服务尚未启动，未切换或下载语音模型。')
        print('JSON情绪动作语音已就绪，正在打开主项目。F4静音。', flush=True)
        player = ROOT / 'MainPlayer-integrated-v1/MGFR.exe'
        args = [str(player), '-mgfr-service-url', 'ws://127.0.0.1:8774/ws',
                '-mgfr-llm-actions', '-mgfr-avatar-data', str(ROOT / 'MainData'),
                '-mgfr-skins', '-mgfr-skin', 'swimsuit', '-mgfr-zmd', '-mgfr-mr-clean-edge',
                '-mgfr-wardrobe', '-mgfr-shoes', '-logFile', str(folder / ('main-' + stamp + '.log'))]
        subprocess.run(args, cwd=player.parent, check=False)
        return 0
    except (OSError, RuntimeError) as error:
        print('启动未完成：', error, file=sys.stderr)
        return 1
    finally:
        for child in reversed(owned):
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
        for log in logs:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
