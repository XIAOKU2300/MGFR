from pathlib import Path
import shutil

lab=Path('H:/MGFR/HandLab-20261018');project=lab/'Project-v5';sources=lab/'Sources/v5'
def ignore(path,names):
    if Path(path).name=='BareHands':return [n for n in names if n=='HandDepthMesh.cs']
    if Path(path).name=='Resources':return [n for n in names if n=='HandDepth.shader']
    return []
for folder in ('Assets','Packages','ProjectSettings'):
    shutil.copytree(lab/'Project-v3'/folder,project/folder,ignore=ignore)
for source in sources.iterdir():
    folder='Editor' if source.name=='SkinnedHandsBuild.cs' else 'Resources' if source.suffix=='.shader' else 'Scripts/BareHands'
    target=project/'Assets/MGFR'/folder/source.name
    with source.open('rb') as reader,target.open('xb') as writer:shutil.copyfileobj(reader,writer)
assets=project/'Assets/MGFR/Resources/BareHands';assets.mkdir()
official=lab/'OfficialPackages/com.unity.xr.hands'
for name in ('LeftHand','RightHand'):
    for suffix in ('.fbx','.fbx.meta'):
        source=official/'Samples~/HandVisualizer/Models'/(name+suffix)
        with source.open('rb') as reader,(assets/source.name).open('xb') as writer:shutil.copyfileobj(reader,writer)
with (assets/'Unity-XR-Hands-LICENSE.md').open('xb') as writer:writer.write((official/'LICENSE.md').read_bytes())
print(project)
