from pathlib import Path
import shutil
lab=Path('H:/MGFR/RenderLab-20261018');source=lab/'Sources/physics-v2';source.mkdir()
for original in (lab/'Sources/physics-v1').glob('*.cs'):
 text=original.read_text(encoding='utf8').replace('"physics/si-physics.json"))));','"physics/si-physics.json")));')
 with (source/original.name).open('x',encoding='utf8') as f:f.write(text)
project=lab/'Project-v5';project.mkdir()
for folder in ('Assets','Packages','ProjectSettings'):
 def ignore(path,names):return [n for n in names if Path(path).name=='PhysicsRig' and n.endswith('.cs')]
 shutil.copytree(lab/'Project-v4'/folder,project/folder,ignore=ignore)
for p in source.glob('*.cs'):
 with p.open('rb') as r,(project/'Assets/MGFR/Scripts/PhysicsRig'/p.name).open('xb') as w:shutil.copyfileobj(r,w)
print(project)
