from pathlib import Path
import argparse
import subprocess
import json
import hashlib
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
BASE=PROJECT/'SiLLMBridge-20261020/MainPlayer-StructuredVoice'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);args=parser.parse_args();output=ROOT/args.name
    if output.parent!=ROOT or output.exists():raise RuntimeError('New direct child output required')
    output.mkdir();work=output/'Build';work.mkdir();source=output/'Source';source.mkdir()
    files=[ROOT/'NativeAvatarActions.cs',ROOT/'NativeClothCoordinator.cs',ROOT/'NativeAcceptance.cs',PROJECT/'unity-client/Assets/MGFR/StructuredVoiceFinal/MainNetworkReview.cs']
    for p in files:
        with (source/p.name).open('xb') as f:f.write(p.read_bytes())
    managed=BASE/'MGFR_Data/Managed';dll=work/'MGFR.StructuredVoiceFinal.dll'
    options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(dll)]
    options+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!='MGFR.StructuredVoiceFinal.dll']
    options+=[str(p) for p in source.glob('*.cs')]
    with (work/'compile.rsp').open('x',encoding='utf-8') as f:f.write('\n'.join('"'+x+'"' for x in options))
    subprocess.run([str(PROJECT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(PROJECT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(work/'compile.rsp')],check=True)
    package=output/'Player';package.mkdir()
    for p in BASE.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(BASE)
        if rel.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:continue
        dest=package/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(p.read_bytes())
    with (package/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll').open('xb') as f:f.write(dll.read_bytes())
    dest=package/'MGFR_Data/StreamingAssets/native-actions'
    for p in (ROOT/'bake-all-v1/Baked').rglob('*'):
        if p.is_file():
            target=dest/p.relative_to(ROOT/'bake-all-v1/Baked');target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as f:f.write(p.read_bytes())
    with (output/'receipt.json').open('x',encoding='utf-8') as f:json.dump({'base':str(BASE),'player':str(package/'MGFR.exe'),'bakedSkins':2,'bakedClipsPerSkin':26,'method':'Unity Humanoid offline bake, standard Animation CrossFade','moduleSha256':hashlib.sha256(dll.read_bytes()).hexdigest()},f,indent=2)
    print('NATIVE_PLAYER_READY',package/'MGFR.exe')
if __name__=='__main__':main()
