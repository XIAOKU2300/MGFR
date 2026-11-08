from pathlib import Path
import shutil
import hashlib
import json
import difflib

lab=Path(__file__).resolve().parent;source=lab.parent/'NaturalIdle-20261019/Project5';project=lab/'Project1'
assert not project.exists()
def once(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)
changes={}
p=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs')
s=(source/p).read_text(encoding='utf-8-sig')
s=once(s,'  int[] anchors;', '''  int[] anchors;
  bool[] longHair;
  public bool FlexibleLongHair {get;}=Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-rigid-long-hair")<0;
  static bool IsLongHair(BodyData d)=>d.group==4&&(d.name.StartsWith("L_hairE_jnt",StringComparison.Ordinal)||d.name.StartsWith("R_hairE_jnt",StringComparison.Ordinal));''')
s=once(s,'for(int warm=0;warm<8;warm++)Tick(1f/120);','for(int warm=0;warm<(FlexibleLongHair?120:8);warm++)Tick(1f/120);')
s=once(s,'   var dynamicOrder=new List<int>();', '   longHair=new bool[count];\n   var dynamicOrder=new List<int>();')
s=once(s,'    rb.isKinematic=Pinned(d);rb.useGravity=false;', '    longHair[i]=IsLongHair(d);\n    rb.isKinematic=Pinned(d);rb.useGravity=false;')
s=once(s,'    rb.solverIterations=32;', '''    if(FlexibleLongHair&&longHair[i]){rb.linearDamping=1.6f;rb.angularDamping=2.8f;}
    rb.solverIterations=32;''')
s=once(s,'    j.targetRotation=Quaternion.identity;j.enableCollision=false;j.enablePreprocessing=true;', '''    if(FlexibleLongHair&&longHair[d.a]&&longHair[d.b])
    {
     // The source PMX locks all angular axes on the 16 links in each long
     // strand. Those are rigid bars, not flexible hair. Keep length/attachment,
     // but allow swing around the capsule's actual longitudinal axis.
     j.axis=Vector3.up;j.secondaryAxis=Vector3.right;
     j.angularXMotion=j.angularYMotion=j.angularZMotion=ConfigurableJointMotion.Limited;
     j.lowAngularXLimit=new SoftJointLimit{limit=-12};j.highAngularXLimit=new SoftJointLimit{limit=12};
     float swing=Bodies[d.a].isKinematic?50:38;
     j.angularYLimit=new SoftJointLimit{limit=swing};j.angularZLimit=new SoftJointLimit{limit=swing};
     j.angularXDrive=j.angularYZDrive=default;
     j.rotationDriveMode=RotationDriveMode.Slerp;
     float spring=b.mass*.12f;
     float inertia=Mathf.Max(b.inertiaTensor.x,Mathf.Max(b.inertiaTensor.y,b.inertiaTensor.z));
     j.slerpDrive=new JointDrive{positionSpring=spring,positionDamper=2*Mathf.Sqrt(spring*inertia),maximumForce=b.mass*.5f};
    }
    j.targetRotation=Quaternion.identity;j.enableCollision=false;j.enablePreprocessing=true;''')
s=once(s,'      rb.AddForce(Vector3.down*1.8f+inertia,ForceMode.Acceleration);',
 '      rb.AddForce(Vector3.down*(FlexibleLongHair&&longHair[i]?9.81f:1.8f)+inertia,ForceMode.Acceleration);')
# Both skins share the long-hair skeleton. Do not re-expand settled hair on F5.
s=once(s,'''   for(int i=0;i<rig.Length;i++)localRest[i]=V(Loader.Data.bones[i].localScaled);
   // Keep proxy collisions''', '''   var hairPositions=new Vector3[Bodies.Length];var hairRotations=new Quaternion[Bodies.Length];
   var hairVelocities=new Vector3[Bodies.Length];var hairSpins=new Vector3[Bodies.Length];
   var keepHair=new bool[Bodies.Length];
   for(int i=0;i<Bodies.Length;i++)if(FlexibleLongHair&&longHair[i]&&!Bodies[i].isKinematic)
   {
    int bone=Data.bodies[i].bone;
    keepHair[i]=(localRest[bone]-V(Loader.Data.bones[bone].localScaled)).sqrMagnitude<.000004f;
    hairPositions[i]=Bodies[i].position;hairRotations[i]=Bodies[i].rotation;
    hairVelocities[i]=Bodies[i].linearVelocity;hairSpins[i]=Bodies[i].angularVelocity;
   }
   for(int i=0;i<rig.Length;i++)localRest[i]=V(Loader.Data.bones[i].localScaled);
   // Keep proxy collisions''')
s=once(s,'''   for(int i=0;i<Bodies.Length;i++)colliders[i].enabled=Data.bodies[i].group<4||used[Data.bodies[i].bone];
   ResetToAnimation();''', '''   for(int i=0;i<Bodies.Length;i++)colliders[i].enabled=Data.bodies[i].group<4||used[Data.bodies[i].bone];
   ResetToAnimation();
   for(int i=0;i<Bodies.Length;i++)if(keepHair[i])
   {
    Bodies[i].position=hairPositions[i];Bodies[i].rotation=hairRotations[i];
    Bodies[i].linearVelocity=hairVelocities[i];Bodies[i].angularVelocity=hairSpins[i];Bodies[i].WakeUp();
   }''')
changes[p]=s
p=Path('Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs')
s=(source/p).read_text(encoding='utf-8-sig')
s=once(s,'a=="-mgfr-natural-idle-review"', 'a=="-mgfr-hair-review"||a=="-mgfr-natural-idle-review"')
changes[p]=s
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(source) in changes]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(source/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
for file in (lab/'Source').glob('*.cs'):
    shutil.copyfile(file,project/'Assets/MGFR/Scripts/Experience/NaturalIdle'/file.name)
patch=[];hashes={}
for p,s in changes.items():
    before=(source/p).read_text(encoding='utf-8-sig')
    patch+=difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix())
    hashes[str(source/p)]=hashlib.sha256((source/p).read_bytes()).hexdigest()
    backup=lab/'Originals'/p;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/p,backup)
with (lab/'hair-fall.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
with (lab/'baseline-hashes.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2)
with (lab/'desktop-no-runtime.json').open('x',encoding='ascii') as f:f.write('{}\n')
print(project)
