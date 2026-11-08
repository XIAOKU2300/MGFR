from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project2';project=lab/'Project3'
assert not project.exists()
review=Path('Assets/MGFR/Skins/SkinSwitchReview.cs')
s=(old/review).read_text(encoding='utf-8')
a='        using (var query = new HandSurfaceQuery(hands.Physics))'
assert s.count(a)==1
s=s.replace(a,'        var query = new HandSurfaceQuery(hands.Physics);')
a='''        SetRest();
        var basePose'''
assert s.count(a)==1
s=s.replace(a,'''        query.Dispose();
        SetRest();
        var basePose''')
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old)==review]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
with (project/review).open('x',encoding='utf-8') as f:f.write(s)
print(project)
