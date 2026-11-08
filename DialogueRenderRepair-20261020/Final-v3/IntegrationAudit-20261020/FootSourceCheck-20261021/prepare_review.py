"""Prepare an isolated review of native foot channels. Never writes live resources."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FINAL = HERE.parents[1]
ACTIVE = FINAL / 'Player'
AUDIT = HERE.parent


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data.encode('utf-8') if isinstance(data, str) else data)


def main():
    # The added ankle->toe direction alignment is not a native animation channel.
    # Remove that alignment at its origin, keeping native source samples untouched.
    source = (AUDIT / 'bind_native_reference.py').read_text(encoding='utf-8')
    source = source.replace("OUT = HERE/'native-reference-v2'", "OUT = HERE/'native-source-feet'")
    source = source.replace('(16,17),', '').replace(',(20,21)', '')
    assert '(16,17)' not in source and '(20,21)' not in source
    exec(compile(source, str(AUDIT / 'bind_native_reference.py'), 'exec'),
         {'__file__': str(HERE / 'native_source_review.py'), '__name__': '__main__'})
    staged = HERE / 'ReviewSource'
    for path in (FINAL / 'Source').rglob('*.cs'):
        text = path.read_text(encoding='utf-8')
        if path.name == 'NativeAvatarActions-main.cs':
            hook = 'var go=new GameObject("Native retargeted avatar actions");'
            assert text.count(hook) == 1
            text = text.replace(hook, 'new GameObject("Native foot source review").AddComponent<FootSourceReview>();' + hook)
        write(staged / path.relative_to(FINAL / 'Source'), text)
    write(staged / 'FootSourceReview.cs', (HERE / 'FootSourceReview.cs').read_bytes())
    managed = ACTIVE / 'MGFR_Data/Managed'
    build = HERE / 'Build'
    build.mkdir(exist_ok=False)
    module = build / 'MGFR.StructuredVoiceFinal.dll'
    options = ['/nologo', '/target:library', '/nostdlib+', '/langversion:latest', '/out:' + str(module)]
    options += ['/reference:' + str(p) for p in managed.glob('*.dll') if p.name != module.name]
    options += [str(p) for p in staged.rglob('*.cs')]
    response = build / 'compile.rsp'
    write(response, '\n'.join('"' + x + '"' for x in options))
    subprocess.run(['H:/MGFR/Editor/Data/NetCoreRuntime/dotnet.exe',
                    'H:/MGFR/Editor/Data/DotNetSdkRoslyn/csc.dll', '@' + str(response)], check=True)
    player = HERE / 'ReviewPlayer'
    player.mkdir(exist_ok=False)
    # New hard links only; the isolated module has its own file and is never linked.
    for path in ACTIVE.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(ACTIVE)
        if rel.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll',
                              'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:
            continue
        target = player / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(path, target)
    write(player / 'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll', module.read_bytes())
    write(HERE / 'review-build.json', json.dumps({'liveModuleSha256': hashlib.sha256((managed / module.name).read_bytes()).hexdigest(),
          'sourceFiles': len(list(staged.rglob('*.cs'))), 'player': str(player / 'MGFR.exe'), 'isolated': True}, indent=2))
    print('Review prepared; live resources unchanged.')


if __name__ == '__main__':
    main()
