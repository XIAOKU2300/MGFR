from pathlib import Path
import hashlib
import json
import shutil

lab = Path(__file__).resolve().parent
base = lab.parent / 'SwimsuitCloth-20261019/Project3'
project = lab / 'Project'
assert base.is_dir() and not project.exists()
receipt = []
for folder in ('Assets', 'ProjectSettings', 'Packages'):
    shutil.copytree(base / folder, project / folder)
for name in ('MrChromaEdgeGuard.cs', 'MrEdgeReview.cs', 'MrEdgeBuild.cs'):
    source = lab / 'Source' / name
    dest = project / ('Assets/MGFR/Editor' if name == 'MrEdgeBuild.cs' else 'Assets/MGFR/Scripts/Rendering') / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as f:
        f.write(source.read_bytes())
    receipt.append({'path': str(dest), 'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()})
# Existing resolved packages are copied into the new project's cache, avoiding downloads.
cache = lab.parent / 'SwimsuitCloth-20261019/Project3/Library/PackageCache'
if cache.is_dir():
    shutil.copytree(cache, project / 'Library/PackageCache')
with (lab / 'prepare-receipt.json').open('x', encoding='utf8') as f:
    json.dump({'base': str(base), 'project': str(project), 'existing_files_overwritten': 0,
               'new_module': receipt}, f, ensure_ascii=False, indent=2)
print(project)
