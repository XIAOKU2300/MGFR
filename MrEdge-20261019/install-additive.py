"""Install only the one new runtime module; never replace an existing file."""
from pathlib import Path
import hashlib
import json

lab = Path(__file__).resolve().parent
source = lab / 'Source/MrChromaEdgeGuard.cs'
dest = lab.parent / 'unity-client/Assets/MGFR/Scripts/Rendering/MrChromaEdgeGuard.cs'
assert not dest.exists(), f'Existing source must not be overwritten: {dest}'
data = source.read_bytes()
assert data == (lab / 'Project/Assets/MGFR/Scripts/Rendering/MrChromaEdgeGuard.cs').read_bytes()
with dest.open('xb') as f:
    f.write(data)
with (lab / 'install-receipt.json').open('x', encoding='utf8') as f:
    json.dump({'new_source': str(dest), 'sha256': hashlib.sha256(data).hexdigest(),
               'existing_files_overwritten': 0, 'alvr_configuration_changed': False}, f, indent=2)
print(dest)
