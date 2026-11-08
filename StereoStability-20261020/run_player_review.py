from pathlib import Path
import argparse,datetime,json,subprocess
root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['render','scale','native','stability','menu'])
parser.add_argument('--player',type=Path,default=root/'Candidate-v1/Player/MGFR.exe')
args=parser.parse_args()
out=root/('Review-'+args.mode+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));out.mkdir()
command=[str(args.player),'-batchmode','-mgfr-noxr','-force-d3d11','-screen-width','900','-screen-height','700','-mgfr-structured-voice','-mgfr-avatar-data',str(root.parent/'SiLLMBridge-20261020/MainData'),'-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-action-port','1','-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(out/'player.log')]
flags={'render':('-mgfr-render-repair-review','-mgfr-render-repair-out',out/'Results'),'scale':('-mgfr-scale-review','-mgfr-scale-review-out',out/'result.json'),'native':('-mgfr-native-review','-mgfr-native-out',out/'Results'),'stability':('-mgfr-stability-review','-mgfr-stability-out',out/'result.json'),'menu':('-mgfr-hand-menu-review','-mgfr-hand-menu-out',out/'Results')}
command.extend(str(value) for value in flags[args.mode])
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
start=datetime.datetime.now(datetime.timezone.utc)
process=subprocess.Popen(command,cwd=args.player.parent,startupinfo=startup)
try:code=process.wait(timeout=170)
except subprocess.TimeoutExpired:
    process.terminate();process.wait(timeout=10)
    raise RuntimeError('Owned verification player timed out; '+str(out)) from None
resultpath=out/'result.json'
if not resultpath.exists():resultpath=out/'Results/result.json'
result=json.loads(resultpath.read_text(encoding='utf-8-sig')) if resultpath.exists() else {}
with (out/'exit.json').open('x',encoding='utf-8') as f:json.dump({'exitCode':code,'exitHex':hex(code&0xffffffff),'seconds':(datetime.datetime.now(datetime.timezone.utc)-start).total_seconds(),'resultExists':resultpath.is_file()},f,indent=2)
print('PLAYER_REVIEW',args.mode,'EXIT',code,'OUTPUT',out,flush=True)
print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
raise SystemExit(0 if code==0 and result.get('pass') else 5)
