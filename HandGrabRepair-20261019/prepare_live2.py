from pathlib import Path
lab=Path(__file__).resolve().parent
project=lab/'Project'
p=project/'Assets/MGFR/Scripts/BareHands/LiveGrabRepairReview.cs'
s=p.read_text(encoding='utf8').replace('LiveGrabRepairReview','LiveGrabRepairReview2').replace('-mgfr-grab-live','-mgfr-grab-live2')
a='   int id=Array.FindIndex(physics.Data.bodies,b=>b.group==groups[test]&&b.mode==1&&!physics.Bodies[b.index].isKinematic);'
b='''   string[] preferred={"裙子_8_0","R_sleeveD_01_jnt_7","L_hairB_05_jnt�N"};
   int id=Array.FindIndex(physics.Data.bodies,b=>b.name==preferred[test]&&!physics.Bodies[b.index].isKinematic);
   if(id<0)id=Array.FindLastIndex(physics.Data.bodies,b=>b.group==groups[test]&&b.mode==1&&!physics.Bodies[b.index].isKinematic);'''
assert s.count(a)==1
s=s.replace(a,b)
with p.with_name('LiveGrabRepairReview2.cs').open('x',encoding='utf8') as f:f.write(s)
p=project/'Assets/MGFR/Editor/GrabRepairBuild.cs'
s=p.read_text(encoding='utf8').replace('GrabRepairBuild','GrabRepairBuild2').replace('Build/Windows/MGFR.exe','Build2/Windows/MGFR.exe')
with p.with_name('GrabRepairBuild2.cs').open('x',encoding='utf8') as f:f.write(s)
