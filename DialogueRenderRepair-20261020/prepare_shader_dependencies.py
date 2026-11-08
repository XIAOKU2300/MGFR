"""Resolve Endfield clothing's UsePass against the renamed shader inside the bundle."""
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE, OUT = HERE / 'ShaderProject-v3', HERE / 'ShaderProject-v4'
OUT.mkdir(exist_ok=False)
for relative in ['Assets', 'Packages', 'ProjectSettings']:
    for path in (BASE / relative).rglob('*'):
        if not path.is_file() or path.suffix == '.meta' or path.name == 'packages-lock.json':
            continue
        if relative == 'ProjectSettings' and path.name != 'ProjectVersion.txt':
            continue
        data = path.read_bytes()
        if path.suffix in ['.shader', '.cs']:
            text = data.decode('utf-8').replace('UsePass "MGFR/StylizedCharacter/FINE_OUTLINE"', 'UsePass "MGFR/StylizedCharacter/MrCoverage/FINE_OUTLINE"')
            if path.suffix == '.cs':
                text = text.replace('ShaderBundle-v3', 'ShaderBundle-v4')
            data = text.encode('utf-8')
        target = OUT / path.relative_to(BASE)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
print('RESOLVED_SHADER_PROJECT', OUT)
