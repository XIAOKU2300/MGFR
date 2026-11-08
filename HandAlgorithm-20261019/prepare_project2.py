from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
root=Path('H:/MGFR/unity-client')
project=lab/'Project2'
assert not project.exists()
candidate=lab/'Candidate'
replaced={p.relative_to(candidate) for p in candidate.rglob('*') if p.is_file()}
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(root) in replaced]
shutil.copytree(root/'Assets',project/'Assets',ignore=ignore)
shutil.copytree(root/'ProjectSettings',project/'ProjectSettings')
shutil.copytree(Path('H:/MGFR/HandLab-20261018/Algorithm-v14/Test-2/Packages'),project/'Packages')
for p in replaced:
 dest=project/p;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write((candidate/p).read_bytes())
source=lab/'Project/Assets/MGFR/Editor/AlgorithmReview.cs'
with (project/'Assets/MGFR/Editor/AlgorithmReview.cs').open('xb') as f:f.write(source.read_bytes())
print(project)
