from pathlib import Path
import datetime
import json
import subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
output=HERE/('scale-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));output.mkdir()
player=HERE/'Final-v2/Player/MGFR.exe'
cmd=[str(player),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-structured-voice','-mgfr-avatar-data',str(ROOT/'SiLLMBridge-20261020/MainData'),'-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-action-port','1','-mgfr-scale-review','-mgfr-scale-review-out',str(output/'result.json'),'-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(output/'player.log')]
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
with (output/'startup.log').open('xb') as stream:
    child=subprocess.Popen(cmd,cwd=player.parent,stdout=stream,stderr=stream,startupinfo=startup)
    try:code=child.wait(timeout=65)
    except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned scale probe timed out') from None
result=json.loads((output/'result.json').read_text(encoding='utf-8-sig'))
print(json.dumps({'exitCode':code,'result':result,'output':str(output)},indent=2),flush=True)
raise SystemExit(0 if code==0 and result['pass'] else 1)
