"""Compile the existing active module with the additive observation component."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
ACTIVE=ROOT/'DialogueRenderRepair-20261020/Final-v3'


def build():
    target=HERE/'Builds'/('candidate-'+uuid.uuid4().hex)
    source=target/'Source';source.mkdir(parents=True)
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ACTIVE/'Source').rglob('*.cs')}
    before[str(ACTIVE/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll')]=hashlib.sha256((ACTIVE/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll').read_bytes()).hexdigest()
    for path in (ACTIVE/'Source').rglob('*.cs'):
        text=path.read_text(encoding='utf-8-sig')
        if path.name=='NativeAvatarActions-main.cs':
            anchor='go.AddComponent<MainAvatarActions>();'
            if text.count(anchor)!=1:raise ValueError('Current bootstrap differs; refusing automatic patch')
            text=text.replace(anchor,anchor+'\n   if(Array.IndexOf(args,"-mgfr-dialogue-context")>=0)go.AddComponent<MgfrInteractionContext>();')
            text=text.replace(anchor,anchor+'\n   if(Array.IndexOf(args,"-mgfr-context-review")>=0)go.AddComponent<MgfrContextReview>();')
        staged=source/path.relative_to(ACTIVE/'Source');staged.parent.mkdir(parents=True,exist_ok=True)
        with staged.open('x',encoding='utf-8') as stream:stream.write(text)
    shutil.copyfile(HERE/'MgfrInteractionContext.cs',source/'MgfrInteractionContext.cs')
    shutil.copyfile(HERE/'MgfrContextReview.cs',source/'MgfrContextReview.cs')
    managed=ACTIVE/'Player/MGFR_Data/Managed'
    module=target/'MGFR.StructuredVoiceFinal.dll'
    args=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(module)]
    args+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!='MGFR.StructuredVoiceFinal.dll']
    args += [str(p) for p in source.rglob('*.cs')]
    response=target/'compile.rsp'
    with response.open('x',encoding='utf-8') as stream:stream.write('\n'.join('"'+x+'"' for x in args))
    subprocess.run([str(ROOT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(ROOT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(response)],check=True)
    player=target/'Player'
    shutil.copytree(ACTIVE/'Player',player,ignore=shutil.ignore_patterns('MGFR.StructuredVoiceFinal.dll','MGFR.StructuredVoiceFinal.pdb'))
    shutil.copyfile(module,player/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll')
    receipt={'activeBase':str(ACTIVE),'source':str(source),'player':str(player/'MGFR.exe'),'module':str(module),'sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'baseHashes':before}
    with (target/'receipt.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
    print(json.dumps(receipt))


if __name__=='__main__':build()
