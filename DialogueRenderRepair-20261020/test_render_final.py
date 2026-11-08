from pathlib import Path
import datetime
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
output = HERE / ('render-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
output.mkdir()
player = HERE / 'Current/Player/MGFR.exe'
command = [str(player), '-batchmode', '-mgfr-noxr', '-force-d3d11', '-mgfr-structured-voice', '-mgfr-avatar-data', str(ROOT / 'SiLLMBridge-20261020/MainData'), '-mgfr-skins', '-mgfr-skin', 'swimsuit', '-mgfr-zmd', '-mgfr-wardrobe', '-mgfr-shoes', '-mgfr-render-repair-review', '-mgfr-render-repair-out', str(output / 'Results'), '-logFile', str(output / 'player.log')]
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
with (output / 'startup.log').open('xb') as stream:
    child = subprocess.Popen(command, cwd=player.parent, stdout=stream, stderr=stream, startupinfo=startup)
    try:
        code = child.wait(timeout=70)
    except subprocess.TimeoutExpired:
        child.terminate()
        child.wait(timeout=10)
        print('OWNED_RENDER_PROBE_TIMEOUT', str(output), flush=True)
        raise SystemExit(2)
result = json.loads((output / 'Results/result.json').read_text(encoding='utf-8-sig'))
print(json.dumps({'exitCode': code, 'result': result, 'output': str(output)}, ensure_ascii=False, indent=2), flush=True)
raise SystemExit(0 if code == 0 and result['pass'] else 1)
