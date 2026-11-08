from pathlib import Path
import sys,shutil,json
root=Path('H:/MGFR');lab=root/'RenderLab-20261018';version=sys.argv[1] if len(sys.argv)>1 else 'v1'
project=lab/('Project-'+version)
project.mkdir(exist_ok=False)
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(root/'unity-client'/folder,project/folder)
runtime=project/'Assets/MGFR/Scripts/Rendering';runtime.mkdir(exist_ok=False)
editor=project/'Assets/MGFR/Editor'
for p in (lab/'Sources'/version).iterdir():
 if p.suffix=='.shader':
  dst=project/'Assets/MGFR/Resources'/p.name;dst.parent.mkdir(exist_ok=True)
 elif p.name=='StylizedBuild.cs':dst=editor/p.name
 else:dst=runtime/p.name
 with p.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
asset=project/'Assets/StreamingAssets/stylized';asset.mkdir(exist_ok=False)
original=next(root.glob('【明日方舟*祀*'))/'other tex'
names=['T_actor_common_matcap_08_D.png','T_actor_jsspsi_face_01_N.png','T_actor_common_female_face_01_SDF.png','T_actor_jsspsi_face_01_ST.png','T_actor_jsspsi_body_01_N.png','T_actor_jsspsi_cloth_01_N.png','T_actor_jsspsi_cloth_01_P.png','T_actor_jsspsi_cloth_02_N.png','T_actor_jsspsi_cloth_02_P.png','T_actor_jsspsi_hair_01_HN.png','T_actor_jsspsi_hair_01_ST.png']
for name in names:
 with (original/name).open('rb') as r,(asset/name).open('xb') as w:shutil.copyfileobj(r,w)
with (lab/('assets-'+version+'.json')).open('x',encoding='utf8') as f:json.dump(names,f,indent=2)
print(project)
