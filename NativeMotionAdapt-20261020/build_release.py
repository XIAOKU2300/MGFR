"""Rebuild current native motion module to a NEW package; no existing files overwritten."""
from pathlib import Path
import argparse
import json
import subprocess
import hashlib
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'Current/Player'
SOURCE=ROOT/'Current/Source'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT) or output==ROOT or output.exists():parser.error('Output must be a NEW child directory of this native-motion delivery')
    output.mkdir(parents=True);work=output/'Build';work.mkdir();src=output/'Source';src.mkdir()
    for path in SOURCE.glob('*.cs'):
        with (src/path.name).open('xb') as f:f.write(path.read_bytes())
    managed=BASE/'MGFR_Data/Managed';plugin=work/'MGFR.StructuredVoiceFinal.dll'
    options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(plugin)]
    options+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!='MGFR.StructuredVoiceFinal.dll']
    options += [str(p) for p in src.glob('*.cs')]
    with (work/'compile.rsp').open('x',encoding='utf-8') as f:f.write('\n'.join('"'+x+'"' for x in options))
    subprocess.run([str(ROOT.parent/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(ROOT.parent/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(work/'compile.rsp')],check=True)
    player=output/'Player';player.mkdir()
    for path in BASE.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(BASE)
        if rel.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:continue
        dest=player/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(path.read_bytes())
    with (player/'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll').open('xb') as f:f.write(plugin.read_bytes())
    with (output/'receipt.json').open('x',encoding='utf-8') as f:json.dump({'base':str(BASE),'source':str(SOURCE),'moduleSha256':hashlib.sha256(plugin.read_bytes()).hexdigest()},f,indent=2)
    print('NEW_NATIVE_PACKAGE',player/'MGFR.exe')
if __name__=='__main__':main()
