"""Build an isolated offline baker from the Current player, with exclusive outputs."""
from pathlib import Path
import argparse, hashlib, json, subprocess

ROOT=Path('H:/MGFR')
PACK=Path(__file__).resolve().parent
CURRENT=ROOT/'NativeMotionAdapt-20261020/Current/Player'

def copy_new(source, destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as f:f.write(source.read_bytes())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--converted',default=str(PACK/'converted-story'));parser.add_argument('--manifest',default='manifest-complete.json');parser.add_argument('--work',default=str(PACK/'bake-story'));args=parser.parse_args()
    converted=Path(args.converted);work=Path(args.work);work.mkdir(exist_ok=False)
    data=work/'Data';(data/'motions').mkdir(parents=True)
    copy_new(ROOT/'SiLLMBridge-20261020/MainData/source-rig.json',data/'source-rig.json')
    copy_new(converted/'motions'/args.manifest,data/'motions/manifest.json')
    manifest=json.loads((data/'motions/manifest.json').read_text(encoding='utf-8'))
    for clip in manifest['clips']:copy_new(converted/'motions'/clip['file'],data/'motions'/clip['file'])
    build=work/'Build';build.mkdir()
    source=ROOT/'NativeMotionAdapt-20261020/bake-all-source-v1/AvatarBake.cs'
    copy_new(source,build/'AvatarBake.cs')
    managed=CURRENT/'MGFR_Data/Managed';dll=build/'MGFR.StructuredVoiceFinal.dll'
    options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(dll)]
    options+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!='MGFR.StructuredVoiceFinal.dll']
    options+=[str(build/'AvatarBake.cs')]
    response=build/'compile.rsp'
    with response.open('x',encoding='utf-8') as f:f.write('\n'.join('"'+x+'"' for x in options))
    subprocess.run([str(ROOT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(ROOT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(response)],check=True)
    player=work/'Player';player.mkdir()
    for p in CURRENT.rglob('*'):
        if not p.is_file():continue
        relative=p.relative_to(CURRENT)
        if relative.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:continue
        copy_new(p,player/relative)
    copy_new(dll,player/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll')
    receipt=dict(base_player=str(CURRENT),base_action_module_sha256=hashlib.sha256((managed/'MGFR.StructuredVoiceFinal.dll').read_bytes()).hexdigest(),baker_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),clips=len(manifest['clips']),purpose='Offline resource baking only; no original runtime files or voice settings changed.')
    with (work/'build-receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2)
    command=[str(player/'MGFR.exe'),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-avatar-bake','-mgfr-avatar-data',str(data),'-mgfr-bake-out',str(work/'Baked'),'-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(work/'bake.log')]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    print('Offline Current bake starting',len(manifest['clips']),'clips x 2 skins',flush=True)
    child=subprocess.Popen(command,cwd=player,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
    try:code=child.wait(timeout=300)
    except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise
    print('Bake exit',code,flush=True)
    for skin in ['swimsuit','original']:
        print(skin,len(list((work/'Baked'/skin).glob('*.hpose'))),flush=True)
    if code:raise SystemExit(code)

if __name__=='__main__':main()
