"""Run continuity review in the real desktop player, without network or microphone."""
from pathlib import Path
import argparse
import subprocess
import json
import time

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('package');parser.add_argument('--output',required=True);args=parser.parse_args()
    package=(ROOT/args.package).resolve();output=(ROOT/args.output).resolve()
    if package.parent!=ROOT or output.parent!=ROOT or output.exists():raise RuntimeError('Requires existing package and NEW review directory')
    output.mkdir();player=package/'Player/MGFR.exe'
    cmd=[str(player),'-batchmode','-mgfr-noxr','-force-d3d11','-screen-width','960','-screen-height','800',
         '-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-structured-voice','-mgfr-avatar-data',str(ROOT.parent/'SiLLMBridge-20261020/MainData'),
         '-mgfr-motion-review','-mgfr-motion-out',str(output/'Continuity'),'-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(output/'player.log')]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    with (output/'startup.log').open('xb') as f:
        child=subprocess.Popen(cmd,cwd=player.parent,stdout=f,stderr=f,startupinfo=startup)
        try:code=child.wait(timeout=120)
        except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned review process timed out') from None
    path=output/'Continuity/result.json'
    print('exitCode',code,'result',str(path),flush=True)
    if path.exists():
        result=json.loads(path.read_text(encoding='utf-8-sig'));print(json.dumps({k:v for k,v in result.items() if k!='components'},ensure_ascii=False,indent=2))
    else:print((output/'player.log').read_text(encoding='utf-8-sig',errors='replace')[-5000:])

if __name__=='__main__':main()
