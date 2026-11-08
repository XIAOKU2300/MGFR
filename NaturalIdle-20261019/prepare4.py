from pathlib import Path
import shutil
import difflib
import hashlib
import json

lab=Path(__file__).resolve().parent;main=lab.parent/'unity-client'
old=lab/'Project3';project=lab/'Project4'
assert not project.exists()
p=Path('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs')
s=(old/p).read_text(encoding='utf-8')
s=s.replace('''                var calmRotation=ArmChain(index)?speechRest[index]:rotations[restFrame,i];''',
'''                var calmRotation=ArmChain(index)?speechRest[index]:rotations[restFrame,i];
                if(index==35||index==61)calmRotation*=Quaternion.Euler(8,0,0);
                if((index>=43&&index<=54)||(index>=69&&index<=80))
                {
                    int digit=(index>=69?index-69:index-43),joint=digit%3,finger=digit/3;
                    float curl=joint==0?14+finger*2:joint==1?10+finger:5+finger;
                    calmRotation=Quaternion.Euler(0,0,(index>=69?1:-1)*curl);
                }
                if((index>=40&&index<=42)||(index>=66&&index<=68))
                    calmRotation=Quaternion.Slerp(Quaternion.identity,rotations[restFrame,i],.3f);''')
s=s.replace('''            // The source idle comes from another costume. Keep the elbows just''',
'''            // The source clip has no spine-14 track. Drive it explicitly from
            // the current skin's rest pose, otherwise the middle breath layer is
            // silently absent. Assign absolute deltas to avoid accumulation.
            float midWeight=naturalBlend*(1-.35f*speech.Weight);
            bones[14].localPosition=rest[14]+Natural.Translation(14,seconds)*midWeight;
            bones[14].localRotation=Quaternion.Euler(Natural.Angles(14,seconds)*midWeight);
            bones[14].localScale=Vector3.one+new Vector3(.0025f,.0008f,.004f)*
                ((Natural.Breath(seconds,.06f)-.44f)*midWeight);
            // The source idle comes from another costume. Keep the elbows just''')
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old)==p]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)

paths=[Path(n) for n in ('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs',
 'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs','Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs')]
paths+=list(x.relative_to(project) for d in ('Assets/MGFR/Scripts/Experience/NaturalIdle','Assets/MGFR/Skins/ClothPhysics') for x in (project/d).glob('*.cs'))
patch=[];hashes={};candidate={}
for rel in paths:
    before=(main/rel).read_text(encoding='utf-8-sig') if (main/rel).exists() else ''
    after=(project/rel).read_text(encoding='utf-8-sig')
    patch+=difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix())
    candidate[rel.as_posix()]=hashlib.sha256((project/rel).read_bytes()).hexdigest()
    if (main/rel).exists():hashes[str(main/rel)]=hashlib.sha256((main/rel).read_bytes()).hexdigest()
with (lab/'ready-to-review.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
with (lab/'baseline-ready.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2)
with (lab/'candidate-ready.json').open('x',encoding='utf-8') as f:json.dump(candidate,f,indent=2)
print(project)
