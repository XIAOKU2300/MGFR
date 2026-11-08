from pathlib import Path
import shutil

lab=Path('H:/MGFR/HandLab-20261018');old=lab/'Project-v11-final';new=lab/'Project-v12'
assert not new.exists()
changes={}
p=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs')
s=(old/p).read_text(encoding='utf8')
s=s.replace('const float Step=1f/120f;','public bool PreciseContacts;\n  float Step=>PreciseContacts?1f/240f:1f/120f;')
s=s.replace('rb.solverIterations=16;rb.solverVelocityIterations=4;', 'rb.solverIterations=32;rb.solverVelocityIterations=8;')
s=s.replace('j.projectionDistance=.008f;j.projectionAngle=15;', 'j.projectionDistance=.0025f;j.projectionAngle=8;')
changes[p]=s
p=Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs');s=(old/p).read_text(encoding='utf8')
s=s.replace('if(ballOwner==h)controllers.Ball.position=f.PinchPoint;\n   }\n  }','if(ballOwner==h)controllers.Ball.position=f.PinchPoint;\n   }\n   Physics.PreciseContacts=ActiveColliders>0;\n  }')
assert 'Physics.PreciseContacts=ActiveColliders>0;' in s
changes[p]=s
p=Path('Assets/MGFR/Scripts/BareHands/ContactStressReview.cs');s=(old/p).read_text(encoding='utf8')
s=s.replace('int total=360;', 'string worstBody="";int worstFrame=0;\n   int total=360;')
before='maxViolation=Mathf.Max(maxViolation,Mathf.Max(Error(j.xMotion,Vector3.Dot(delta,x)),Mathf.Max(Error(j.yMotion,Vector3.Dot(delta,y)),Error(j.zMotion,Vector3.Dot(delta,z)))));'
after='float violation=Mathf.Max(Error(j.xMotion,Vector3.Dot(delta,x)),Mathf.Max(Error(j.yMotion,Vector3.Dot(delta,y)),Error(j.zMotion,Vector3.Dot(delta,z))));\n     if(violation>maxViolation){maxViolation=violation;worstBody=j.name;worstFrame=f;}'
assert before in s;s=s.replace(before,after)
s=s.replace('maxConstraintViolationMetres={maxViolation}\\n','maxConstraintViolationMetres={maxViolation}\\nworstBody={worstBody}\\nworstFrame={worstFrame}\\n')
changes[p]=s
names={p.name for p in changes}
def ignore(path,items):return [n for n in items if n in names]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,new/folder,ignore=ignore)
for p,s in changes.items():
 with (new/p).open('x',encoding='utf8') as f:f.write(s)
print(new)
