"""Run packaged real Unity regressions in isolated output directories."""
import argparse,json,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--player',type=Path,default=ROOT/'Build/Windows/MGFR.exe');p.add_argument('--run',required=True);p.add_argument('--cases',nargs='+',default=['quality','coexist','controller','hands','chat','contact']);a=p.parse_args()
out=ROOT/'Review'/a.run;out.mkdir(exist_ok=False)
cases={'quality':['-mgfr-hand-quality-review','-mgfr-quality-output'],
       'compat':['-mgfr-quality-compat-review','-mgfr-quality-output'],
       'temporal':['-mgfr-hand-temporal-review','-mgfr-hand-dir'],
       'coexist':['-mgfr-coexist-review','-mgfr-check-dir'],
       'controller':['-mgfr-controller-review','-mgfr-check-dir'],
       'hands':['-mgfr-hand-review','-mgfr-hand-dir'],
       'chat':['-mgfr-chat-review','-mgfr-chat-dir'],
       'contact':['-mgfr-contact-stress','-mgfr-stress-dir'],
       'original':['-mgfr-mr-edge-review','-mgfr-mr-edge-output'],
       'swimsuit':['-mgfr-mr-edge-review','-mgfr-mr-edge-output']}
results=[]
for name in a.cases:
 folder=out/name;folder.mkdir();log=folder/'player.log'
 args=[str(a.player),'-batchmode','-mgfr-noxr','-force-d3d11','-screen-width','1280','-screen-height','960','-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-skins','-mgfr-zmd','-mgfr-mr-clean-edge','-mgfr-mr-edge-force',*cases[name],str(folder),'-logFile',str(log)]
 if name in ['coexist','controller']:args+=['-mgfr-wardrobe','-mgfr-shoes','-mgfr-skin','swimsuit']
 if name=='compat':args+=['-mgfr-structured-voice','-mgfr-avatar-data',str(ROOT.parent/'SiLLMBridge-20261020/MainData')]
 if name=='swimsuit':args+=['-mgfr-skin','swimsuit']
 begin=time.monotonic()
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
 child=subprocess.Popen(args,cwd=a.player.parent,startupinfo=startup)
 try:code=child.wait(timeout=180)
 except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);code=-1
 text=log.read_text(encoding='utf-8-sig',errors='replace') if log.exists() else ''
 issues=[line for line in text.splitlines() if any(word in line for word in ['Exception:','Shader error','error CS','NullReferenceException'])]
 item={'case':name,'exitCode':code,'seconds':round(time.monotonic()-begin,2),'errors':issues[:20],'log':str(log)};results.append(item)
 print(json.dumps(item,ensure_ascii=False),flush=True)
with (out/'results.json').open('x',encoding='utf-8') as f:json.dump(results,f,indent=2,ensure_ascii=False)
raise SystemExit(0 if all(x['exitCode']==0 and not x['errors'] for x in results) else 1)
