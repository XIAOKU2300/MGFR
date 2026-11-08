from pathlib import Path
import subprocess
import json
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
BASE=PROJECT/'SiLLMBridge-20261020/MainPlayer-StructuredVoice'
def main():
    output=ROOT/'avatar-probe-v1';output.mkdir(exist_ok=False);work=output/'Build';work.mkdir()
    managed=BASE/'MGFR_Data/Managed';dll=work/'MGFR.StructuredVoiceFinal.dll'
    options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(dll)]
    options+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!='MGFR.StructuredVoiceFinal.dll']
    options+=[str(ROOT/'AvatarBake.cs')]
    response=work/'compile.rsp'
    with response.open('x',encoding='utf-8') as f:f.write('\n'.join('"'+x+'"' for x in options))
    subprocess.run([str(PROJECT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(PROJECT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(response)],check=True)
    player=output/'Player';player.mkdir()
    for p in BASE.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(BASE)
        if rel.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:continue
        dest=player/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(p.read_bytes())
    with (player/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll').open('xb') as f:f.write(dll.read_bytes())
    log=output/'bake.log';out=output/'Baked';exe=player/'MGFR.exe'
    args=[str(exe),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-avatar-bake','-mgfr-avatar-data',str(PROJECT/'SiLLMBridge-20261020/MainData'),'-mgfr-bake-out',str(out),'-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(log)]
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    child=subprocess.Popen(args,cwd=player,startupinfo=startup)
    try:code=child.wait(timeout=90)
    except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise
    print('exit',code,'report',str(out/'avatar-report.txt'),flush=True)
    if (out/'avatar-report.txt').exists():print((out/'avatar-report.txt').read_text(encoding='utf-8-sig'))
    else:print(log.read_text(encoding='utf-8-sig',errors='replace')[-6000:])
if __name__=='__main__':main()
