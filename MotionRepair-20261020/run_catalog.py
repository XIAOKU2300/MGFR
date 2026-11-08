"""Exercise every enabled clip in the real release player, isolated from live voice."""
from pathlib import Path
import subprocess
import datetime
import json

ROOT=Path(__file__).resolve().parent
def main():
    output=ROOT/('catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));output.mkdir()
    player=ROOT/'release-v1/Player/MGFR.exe'
    args=[str(player),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-action-port','1',
          '-mgfr-structured-voice','-mgfr-avatar-data',str(ROOT.parent/'SiLLMBridge-20261020/MainData'),'-mgfr-catalog-review','-mgfr-catalog-out',str(output/'Catalog'),
          '-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(output/'player.log')]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    with (output/'startup.log').open('xb') as f:
        child=subprocess.Popen(args,cwd=player.parent,stdout=f,stderr=f,startupinfo=startup)
        try:code=child.wait(timeout=180)
        except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned catalog review timed out') from None
    result=json.loads((output/'Catalog/result.json').read_text(encoding='utf-8-sig'))
    print(json.dumps({'pass':result['pass'],'exitCode':code,'supported':result['supported'],'blocked':result['blocked'],'frames':result['totalFrames'],'spikes':sum(c['spikes'] for c in result['clips']),'result':str(output/'Catalog/result.json')},ensure_ascii=False),flush=True)
    raise SystemExit(0 if code==0 and result['pass'] else 1)
if __name__=='__main__':main()
