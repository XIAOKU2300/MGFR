from pathlib import Path
import shutil
root=Path('H:/MGFR');lab=root/'HandLab-20261018';project=lab/'Project-v1';project.mkdir()
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(root/'unity-client'/folder,project/folder)
for source in (lab/'OfficialPackages').iterdir():shutil.copytree(source,project/'Packages'/source.name)
target=project/'Assets/MGFR/Scripts/BareHands';target.mkdir()
for source in (lab/'Sources/v1').iterdir():
 if source.suffix=='.shader':dst=project/'Assets/MGFR/Resources'/source.name
 elif source.name=='HandsBuild.cs':dst=project/'Assets/MGFR/Editor'/source.name
 else:dst=target/source.name
 with source.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
print(project)
