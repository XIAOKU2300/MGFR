from pathlib import Path
import argparse
import subprocess
import datetime
import json
ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package',default='Current');args=parser.parse_args()
    package=ROOT/args.package
    if package.parent!=ROOT:raise RuntimeError('Package must be a direct child')
    output=ROOT/('acceptance-'+args.package+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));output.mkdir()
    exe=package/'Player/MGFR.exe'
    cmd=[str(exe),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-structured-voice','-mgfr-avatar-data',str(ROOT.parent/'SiLLMBridge-20261020/MainData'),
         '-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-action-port','1','-mgfr-native-review','-mgfr-native-out',str(output/'Results'),
         '-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(output/'player.log')]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    with (output/'startup.log').open('xb') as f:
        child=subprocess.Popen(cmd,cwd=exe.parent,stdout=f,stderr=f,startupinfo=startup)
        try:code=child.wait(timeout=150)
        except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned native review timed out') from None
    result=output/'Results/result.json'
    print('exit',code,'result',str(result),flush=True)
    if result.exists():print(result.read_text(encoding='utf-8-sig'))
    else:print((output/'player.log').read_text(encoding='utf-8-sig',errors='replace')[-6000:])
    raise SystemExit(code)
if __name__=='__main__':main()
