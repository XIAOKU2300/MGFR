from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent;old=lab/'Project1';project=lab/'Project2';assert not project.exists()
p=Path('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs');s=(old/p).read_text(encoding='utf-8-sig')
a='if(index==0||index==1||index==3||(index>=6&&index<=11))calmRotation=Quaternion.identity;'
b='if(index==0||index==1||index==3||index==5||index==12||(index>=6&&index<=11))calmRotation=Quaternion.identity;'
assert s.count(a)==1;s=s.replace(a,b)
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old)==p]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print(project)
