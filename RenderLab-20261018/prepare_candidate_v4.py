from pathlib import Path
import shutil
root=Path('H:/MGFR');lab=root/'RenderLab-20261018';project=lab/'Project-v4'
project.mkdir(exist_ok=False)
for folder in ('Assets','Packages','ProjectSettings'):
 shutil.copytree(lab/'Project-v3'/folder,project/folder)
target=project/'Assets/MGFR/Scripts/PhysicsRig';target.mkdir()
for source in (lab/'Sources/physics-v1').glob('*.cs'):
 with source.open('rb') as r,(target/source.name).open('xb') as w:shutil.copyfileobj(r,w)
target=project/'Assets/StreamingAssets/physics';target.mkdir()
with (lab/'pmx-physics-survey.json').open('rb') as r,(target/'si-physics.json').open('xb') as w:shutil.copyfileobj(r,w)
print(project)
