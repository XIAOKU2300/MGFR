"""Run a bounded desktop review of the actual Unity hand panel."""
from pathlib import Path
import argparse
import datetime
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def run(player, no_capture=False):
    output = HERE / 'MenuBuild' / ('Review-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    output.mkdir(parents=True, exist_ok=False)
    command = [str(player), '-batchmode', '-mgfr-noxr', '-force-d3d11',
        '-mgfr-structured-voice', '-mgfr-avatar-data', str(ROOT / 'SiLLMBridge-20261020/MainData'),
        '-mgfr-service-url', 'ws://127.0.0.1:1/ws', '-mgfr-action-port', '1',
        '-mgfr-skins', '-mgfr-skin', 'swimsuit', '-mgfr-zmd', '-mgfr-wardrobe', '-mgfr-shoes',
        '-mgfr-hand-menu-review', '-mgfr-hand-menu-out', str(output / 'Results'),
        '-logFile', str(output / 'player.log')]
    if no_capture:
        command.append('-mgfr-hand-menu-no-capture')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen(command, cwd=player.parent, startupinfo=startup)
    try:
        code = process.wait(timeout=75)
    except subprocess.TimeoutExpired:
        process.terminate()
        process.wait(timeout=10)
        raise RuntimeError('Hand menu review timed out: ' + str(output)) from None
    result_path = output / 'Results/result.json'
    print('HAND_MENU_REVIEW_OUTPUT', output, flush=True)
    if result_path.is_file():
        result = json.loads(result_path.read_text(encoding='utf-8-sig'))
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return 0 if result['pass'] and code == 0 else 5
    log = (output / 'player.log').read_text(encoding='utf-8-sig', errors='replace')
    for line in log.splitlines():
        if any(word in line for word in ['Exception:', 'HAND_PANEL_', 'MGFR_HAND_MENU', 'error CS']):
            print(line[:400])
    return code if code else 6

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--player', type=Path, default=HERE / 'Player/MGFR.exe')
    parser.add_argument('--no-capture', action='store_true')
    args = parser.parse_args()
    raise SystemExit(run(args.player.resolve(strict=True), args.no_capture))
