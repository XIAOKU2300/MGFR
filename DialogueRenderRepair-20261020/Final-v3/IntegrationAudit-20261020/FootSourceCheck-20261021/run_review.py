from pathlib import Path
import os
import subprocess
HERE=Path(__file__).resolve().parent
env=dict(os.environ,XR_RUNTIME_JSON=str(HERE/'disabled-xr-runtime.json'))
exe=HERE/'ReviewPlayer/MGFR.exe'
cmd=[str(exe),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-structured-voice','-mgfr-avatar-data','H:/MGFR/SiLLMBridge-20261020/MainData',
     '-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-action-port','1','-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes',
     '-mgfr-foot-out',str(HERE/'Results'),'-logFile',str(HERE/'player.log')]
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
with (HERE/'startup.log').open('xb') as stream:
    child=subprocess.Popen(cmd,cwd=exe.parent,env=env,startupinfo=startup,stdout=stream,stderr=stream)
    try:code=child.wait(timeout=100)
    except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned isolated review timed out') from None
print('exit',code,'result',HERE/'Results/result.json')
raise SystemExit(code)
