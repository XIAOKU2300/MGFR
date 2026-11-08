from pathlib import Path
import hashlib,json,shutil,subprocess,sys
root=Path(__file__).resolve().parent
active=root.parent/'DialogueRenderRepair-20261020/Final-v3'
out=root/(sys.argv[1] if len(sys.argv)>1 else 'Candidate-v1')
out.mkdir()
source=out/'Source'
shutil.copytree(active/'Source',source)
hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in (active/'Source').rglob('*.cs')}
for path in (active/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll',active/'Player/MGFR_Data/StreamingAssets/mgfr-mr-coverage',active/'Player/MGFR_Data/StreamingAssets/gesture-touch-panel-v1',root.parent/'DialogueRenderRepair-20261020/launch_final.py'):
    hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
main=source/'NativeAvatarActions-main.cs'
text=main.read_text(encoding='utf-8')
before='public static void Install(){MGFR.Repairs.MrClothCoverageRepair.Install();'
assert text.count(before)==1
main.write_text(text.replace(before,before+'MGFR.Repairs.XrSessionRecovery.Install();'),encoding='utf-8')
shutil.copy2(root/'XrSessionRecovery.cs',source/'XrSessionRecovery.cs')
shutil.copy2(root/'StereoMaterialGpuReview.cs',source/'StereoMaterialGpuReview.cs')
build=out/'Build';build.mkdir()
plugin=build/'MGFR.StructuredVoiceFinal.dll'
managed=active/'Player/MGFR_Data/Managed'
options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(plugin)]
options+=['/reference:'+str(path) for path in managed.glob('*.dll') if path.name!=plugin.name]
options+=[str(path) for path in source.rglob('*.cs')]
rsp=build/'compile.rsp'
with rsp.open('x',encoding='utf-8') as f:f.write('\n'.join('"'+option+'"' for option in options))
subprocess.run([str(root.parent/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(root.parent/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(rsp)],check=True)
shutil.copytree(active/'Player',out/'Player')
shutil.copy2(plugin,out/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll')
for name in ('mgfr-mr-coverage','gesture-touch-panel-v1'):
    shutil.copy2(root/'Bundle-final'/name,out/'Player/MGFR_Data/StreamingAssets'/name)
with (out/'source-snapshot.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2)
print('CANDIDATE_READY',out,flush=True)
