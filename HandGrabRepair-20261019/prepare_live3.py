from pathlib import Path
lab=Path(__file__).resolve().parent
project=lab/'Project'
p=project/'Assets/MGFR/Scripts/BareHands/LiveGrabRepairReview2.cs'
s=p.read_text(encoding='utf8').replace('LiveGrabRepairReview2','LiveGrabRepairReview3').replace('-mgfr-grab-live2','-mgfr-grab-live3')
s=s.replace('readonly int[] groups={9,5,4};','readonly int[] groups={9,5,4,9};').replace('new int[3]','new int[4]').replace('new float[3]','new float[4]')
s=s.replace('static Pose[] PoseAt(Vector3 point,bool pinch)','static Pose[] PoseAt(Vector3 point,bool pinch,bool narrowOpen=false)')
s=s.replace('   var center=(p[5].position+p[10].position)*.5f;', '   if(!pinch&&narrowOpen)p[5].position=p[10].position+Vector3.left*.060f;\n   var center=(p[5].position+p[10].position)*.5f;')
s=s.replace('hands.Source.SetReplayFrame(0,PoseAt(target,pinch),true);', '''hands.Source.SetReplayFrame(0,PoseAt(target,pinch,test==3),true);
   if(test==3){hands.Source.Frames[0].Radius[5]=.025f;hands.Source.Frames[0].Radius[10]=.025f;}''')
a='   string[] preferred={"裙子_8_0","R_sleeveD_01_jnt_7","L_hairB_05_jnt�N"};'
assert s.count(a)==1
s=s.replace(a,'   string[] preferred={"裙子_8_0","R_sleeveD_01_jnt_7","L_hairE_jnt15","裙子_8_0"};')
s=s.replace('   if(id<0)id=Array.FindLastIndex(physics.Data.bodies,b=>b.group==groups[test]&&b.mode==1&&!physics.Bodies[b.index].isKinematic);','')
s=s.replace('    acquired[test]=grabbed;start=', '''    if(test==2&&!hands.Physics.Data.bodies[grabbed].name.Contains("hair")){Finish(false,"hair fixture acquired a non-hair node");return;}
    acquired[test]=grabbed;start=''' )
s=s.replace('report.Add($"group={groups[test]}; body=', 'report.Add($"test={test}; group={groups[test]}; body=')
with p.with_name('LiveGrabRepairReview3.cs').open('x',encoding='utf8') as f:f.write(s)
p=project/'Assets/MGFR/Editor/GrabRepairBuild2.cs'
s=p.read_text(encoding='utf8').replace('GrabRepairBuild2','GrabRepairBuild3').replace('Build2/Windows/MGFR.exe','Build3/Windows/MGFR.exe')
with p.with_name('GrabRepairBuild3.cs').open('x',encoding='utf8') as f:f.write(s)
