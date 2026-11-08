from pathlib import Path
import shutil
lab=Path('H:/MGFR/HandLab-20261018');source=lab/'Sources/v3';source.mkdir();project=lab/'Project-v3';project.mkdir()
for p in (lab/'Sources/v2').iterdir():
 text=p.read_text(encoding='utf8').replace('loader.GetComponent<LegPlantSolver>().enabled=false;','FindAnyObjectByType<LegPlantSolver>().enabled=false;')
 with (source/p.name).open('x',encoding='utf8') as f:f.write(text)
def ignore(path,names):
 if Path(path).name=='BareHands':return [n for n in names if n.endswith('.cs')]
 if Path(path).name=='Editor':return [n for n in names if n=='HandsBuild.cs']
 if Path(path).name=='Resources':return [n for n in names if n=='HandDepth.shader']
 return []
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(lab/'Project-v2'/folder,project/folder,ignore=ignore)
for p in source.iterdir():
 dst=project/'Assets/MGFR'/('Resources' if p.suffix=='.shader' else 'Editor' if p.name=='HandsBuild.cs' else 'Scripts/BareHands')/p.name
 with p.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
print(project)
