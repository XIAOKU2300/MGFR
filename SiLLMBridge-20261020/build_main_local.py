"""Rebuild only the new module against the working main player, into a NEW package."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'HandCoexist-20261019/Project/Build/Windows'
SOURCE = ROOT.parent / 'unity-client/Assets/MGFR/StructuredVoiceFinal'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT) or output == ROOT or output.exists():
        parser.error('Output must be a NEW child directory of this delivery root')
    output.mkdir(parents=True, exist_ok=False)
    work = output / 'module-build'
    work.mkdir()
    managed = BASE / 'MGFR_Data/Managed'
    plugin = work / 'MGFR.StructuredVoiceFinal.dll'
    options = ['/nologo', '/target:library', '/nostdlib+', '/langversion:latest', '/debug:portable', '/out:' + str(plugin)]
    options += ['/reference:' + str(p) for p in managed.glob('*.dll')]
    options += [str(SOURCE / name) for name in ['MainAvatarActions.cs', 'MainActionsReview.cs', 'MainNetworkReview.cs']]
    with (work / 'compile.rsp').open('x', encoding='utf-8') as f:
        f.write('\n'.join('"' + value + '"' for value in options))
    subprocess.run([str(ROOT.parent / 'Editor/Data/NetCoreRuntime/dotnet.exe'),
                    str(ROOT.parent / 'Editor/Data/DotNetSdkRoslyn/csc.dll'), '@' + str(work / 'compile.rsp')], check=True)
    subprocess.run([r'C:\Program Files\dotnet\dotnet.exe', str(ROOT / 'incremental-final/InjectMainEntryFinal.dll'),
                    str(managed / 'Assembly-CSharp.dll'), str(plugin), str(work / 'Assembly-CSharp.dll'),
                    str(work / 'entry-il-diff.txt')], check=True)
    package = output / 'Player'
    package.mkdir()
    for source in BASE.rglob('*'):
        if not source.is_file():
            continue
        relative = source.relative_to(BASE)
        if relative.as_posix() in ['MGFR_Data/Managed/Assembly-CSharp.dll', 'MGFR_Data/ScriptingAssemblies.json']:
            continue
        target = package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(source.read_bytes())
    for name in ['Assembly-CSharp.dll', 'MGFR.StructuredVoiceFinal.dll', 'MGFR.StructuredVoiceFinal.pdb']:
        with (package / 'MGFR_Data/Managed' / name).open('xb') as f:
            f.write((work / name).read_bytes())
    assemblies = json.loads((BASE / 'MGFR_Data/ScriptingAssemblies.json').read_text())
    assemblies['names'].append('MGFR.StructuredVoiceFinal.dll')
    assemblies['types'].append(16)
    with (package / 'MGFR_Data/ScriptingAssemblies.json').open('x', encoding='utf-8') as f:
        json.dump(assemblies, f)
    with (output / 'receipt.json').open('x', encoding='utf-8') as f:
        json.dump({'player': str(package / 'MGFR.exe'), 'source': str(SOURCE),
                   'base_assembly_sha256': hashlib.sha256((managed / 'Assembly-CSharp.dll').read_bytes()).hexdigest(),
                   'method_changed': 'SiCharacterBootstrap.Awake: one opt-in Install call'}, f, indent=2)
    print('MAIN_PACKAGE_READY', package / 'MGFR.exe')


if __name__ == '__main__':
    main()
