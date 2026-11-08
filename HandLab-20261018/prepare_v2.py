from pathlib import Path
import shutil
lab=Path('H:/MGFR/HandLab-20261018');project=lab/'Project-v2';project.mkdir()
source=lab/'Sources/v2';source.mkdir()
for p in (lab/'Sources/v1').iterdir():
 text=p.read_text(encoding='utf8')
 if p.name=='HandJointSource.cs':text=text.replace('f.Valid[0]&&f.Valid[1];','f.Valid[0]&&f.Valid[1]&&f.Valid[7]&&f.Valid[12]&&f.Valid[17]&&f.Valid[22];')
 with (source/p.name).open('x',encoding='utf8') as f:f.write(text)
def ignore(path,names):
 result=[]
 if Path(path).name=='BareHands':result += [n for n in names if n.endswith('.cs')]
 if Path(path).name=='Editor':result += [n for n in names if n=='HandsBuild.cs']
 if Path(path).name=='Resources':result += [n for n in names if n=='HandDepth.shader']
 if Path(path).name in ('com.unity.xr.hands','com.unity.mathematics'):
  result += [n for n in names if n in ('Tests','Tests.meta','Samples~','Documentation~')]
 return result
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(lab/'Project-v1'/folder,project/folder,ignore=ignore)
for p in source.iterdir():
 if p.suffix=='.shader':dst=project/'Assets/MGFR/Resources'/p.name
 elif p.name=='HandsBuild.cs':dst=project/'Assets/MGFR/Editor'/p.name
 else:dst=project/'Assets/MGFR/Scripts/BareHands'/p.name
 with p.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
print(project)
