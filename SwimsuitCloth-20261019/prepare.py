from pathlib import Path
import hashlib
import json
import shutil

lab=Path(__file__).resolve().parent
main=lab.parent/'unity-client'
project=lab/'Project1'
assert not project.exists()
p=Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs')
s=(main/p).read_text(encoding='utf-8-sig')
a='  public HandJointSource Source {get;private set;}';assert s.count(a)==1
s=s.replace(a,a+'\n  public Func<int,bool> ExternalClothGrab;')
a='''  void AcquireHand(int h,bool afterPhysics)
  {
   if(!acquisitionPending[h])return;'''
b='''  void AcquireHand(int h,bool afterPhysics)
  {
   if(ExternalClothGrab!=null&&ExternalClothGrab(h))
   {Release(h);blockedUntilOpen[h]=true;GrabStatus[h]="泳装布料抓取中";return;}
   if(!acquisitionPending[h])return;'''
assert s.count(a)==1
s=s.replace(a,b)
a='(GrabbedBody[0]>=0||GrabbedBody[1]>=0?"抓取中":"无")';assert s.count(a)==1
s=s.replace(a,'(GrabbedBody[0]>=0||GrabbedBody[1]>=0||(ExternalClothGrab!=null&&(ExternalClothGrab(0)||ExternalClothGrab(1)))?"抓取中":"无")')
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(main)==p]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(main/folder,project/folder,ignore=ignore)
with (project/p).open('x',encoding='utf-8') as f:f.write(s)
module=project/'Assets/MGFR/Skins/ClothPhysics';module.mkdir()
for source in (lab/'Source').glob('*.cs'):shutil.copyfile(source,module/source.name)

skin=lab.parent/'converted/skins/si-swimsuit-barefoot-ankle-v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with (lab/'source-hashes.json').open('x',encoding='utf-8') as f:
 json.dump({str(main/p):sha(main/p),str(skin/'si_model.json'):sha(skin/'si_model.json'),str(skin/'si_model.bin'):sha(skin/'si_model.bin')},f,indent=2)
with (lab/'.gitignore').open('x',encoding='ascii') as f:f.write('/Project*/\n*.log\n')
print(project)
