from pathlib import Path
import shutil,json
root=Path('H:/MGFR');lab=root/'RenderLab-20261018';project=lab/'Project-v3'
project.mkdir(exist_ok=False)
for folder in ('Assets','Packages','ProjectSettings'):
 shutil.copytree(root/'unity-client'/folder,project/folder)
for source in (lab/'Sources/v3').iterdir():
 folder='Resources' if source.suffix=='.shader' else 'Scripts/Rendering'
 target=project/'Assets/MGFR'/folder/source.name
 with source.open('rb') as r,target.open('xb') as w:shutil.copyfileobj(r,w)
original=next(root.glob('【明日方舟*祀*'))/'other tex'
names=['T_actor_common_cloth_04_RD.png','T_actor_common_cloth_04_RS.png','T_actor_common_cloth_02_RS.png','T_actor_jsspsi_cloth_01_E.png','T_actor_jsspsi_cloth_02_E.png']
target=project/'Assets/StreamingAssets/endfield';target.mkdir()
for name in names:
 with (original/name).open('rb') as r,(target/name).open('xb') as w:shutil.copyfileobj(r,w)
print(project)
