from pathlib import Path
import shutil
lab=Path('H:/MGFR/HandLab-20261018');project=lab/'Project-v6';source=lab/'Sources/v6';source.mkdir()
text=(lab/'Sources/v5/HandDepthMesh.cs').read_text(encoding='utf8')
text=text.replace('XRHandJointIDUtility.FromIndex(i).ToString()', '(i==0?XRHandJointID.Palm:i==1?XRHandJointID.Wrist:XRHandJointIDUtility.FromIndex(i)).ToString()')
with (source/'HandDepthMesh.cs').open('x',encoding='utf8') as file:file.write(text)
def ignore(path,names):
    if Path(path).name=='BareHands':return [n for n in names if n=='HandDepthMesh.cs']
    if Path(path).name=='Editor':return [n for n in names if n.startswith('DumpHandHierarchy')]
    return []
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(lab/'Project-v5'/folder,project/folder,ignore=ignore)
with (source/'HandDepthMesh.cs').open('rb') as reader,(project/'Assets/MGFR/Scripts/BareHands/HandDepthMesh.cs').open('xb') as writer:shutil.copyfileobj(reader,writer)
print(project)
