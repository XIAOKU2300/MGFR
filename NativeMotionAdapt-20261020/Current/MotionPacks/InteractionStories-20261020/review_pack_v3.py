from pathlib import Path
import json, subprocess, argparse
ROOT=Path('H:/MGFR');PACK=Path(__file__).resolve().parent;CURRENT=ROOT/'NativeMotionAdapt-20261020/Current/Player'
def cp(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 with dst.open('xb') as f:f.write(src.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',default=str(PACK/'review-story'));p.add_argument('--extra',action='append',default=[]);p.add_argument('--skin',default='swimsuit');a=p.parse_args()
 work=Path(a.work);work.mkdir(exist_ok=False);build=work/'Build';build.mkdir();data=work/'Data';(data/'motions').mkdir(parents=True);baked=work/'Baked'
 manifest=json.loads((ROOT/'SiLLMBridge-20261020/MainData/motions/manifest.json').read_text(encoding='utf-8'))
 for converted in [PACK/'converted-story']+[Path(x) for x in a.extra]:
  name='manifest-complete.json' if (converted/'motions/manifest-complete.json').exists() else 'manifest.json'
  manifest['clips']+=json.loads((converted/'motions'/name).read_text(encoding='utf-8'))['clips']
 with (data/'motions/manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
 expressions=json.loads((ROOT/'SiLLMBridge-20261020/MainData/expressions.json').read_text(encoding='utf-8'))
 addition=PACK/'faces/expressions-additions.json'
 if addition.exists():expressions['poses']+=json.loads(addition.read_text(encoding='utf-8'))['poses']
 with (data/'expressions.json').open('x',encoding='utf-8') as f:json.dump(expressions,f,ensure_ascii=False,indent=2)
 for skin in ['swimsuit','original']:
  for source in [CURRENT/'MGFR_Data/StreamingAssets/native-actions'/skin,PACK/'bake-story/Baked'/skin]+[Path(x)/'Baked'/skin for x in a.extra]:
   for f in source.glob('*.hpose'):cp(f,baked/skin/f.name)
 source=ROOT/'NativeMotionAdapt-20261020/Current/Source'
 sources=[source/'NativeAvatarActions-main.cs',source/'NativeClothCoordinator-production.cs',source/'NativeCatalogReview-current.cs',source/'MainNetworkReview.cs',PACK/'InteractionReview-v3.cs']
 dll=build/'MGFR.StructuredVoiceFinal.dll';managed=CURRENT/'MGFR_Data/Managed'
 options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(dll)]+['/reference:'+str(f) for f in managed.glob('*.dll') if f.name!='MGFR.StructuredVoiceFinal.dll']+[str(s) for s in sources]
 response=build/'compile.rsp'
 with response.open('x',encoding='utf-8') as f:f.write('\n'.join('"'+x+'"' for x in options))
 subprocess.run([str(ROOT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(ROOT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(response)],check=True)
 player=work/'Player';player.mkdir()
 for f in CURRENT.rglob('*'):
  if f.is_file() and f.name not in ['MGFR.StructuredVoiceFinal.dll','MGFR.StructuredVoiceFinal.pdb']:cp(f,player/f.relative_to(CURRENT))
 cp(dll,player/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll')
 command=[str(player/'MGFR.exe'),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-structured-voice','-mgfr-native-review','-mgfr-avatar-data',str(data),'-mgfr-native-data',str(baked),'-mgfr-native-out',str(work/'Screenshots'),'-mgfr-skins','-mgfr-skin',a.skin,'-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(work/'review.log')]
 startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
 process=subprocess.Popen(command,cwd=player,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
 try:code=process.wait(timeout=300)
 except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10);raise
 print('review exit',code,'screenshots',len(list((work/'Screenshots').glob('*.png'))),flush=True)
 if code:raise SystemExit(code)
if __name__=='__main__':main()
