from pathlib import Path
import shutil

lab=Path('H:/MGFR/HandLab-20261018');old=lab/'Project-v12';new=lab/'Project-v13'
assert not new.exists()
changes={}
p=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs');s=(old/p).read_text(encoding='utf8')
s=s.replace('var dynamicOrder=new List<int>();', '''var dynamicOrder=new List<int>();
   // PMX masses encode Bullet priority ratios, not garment masses in kilograms.
   // Keep bounded relative weights within each material group and normalize totals.
   float Weight(BodyData body)=>Mathf.Clamp(Mathf.Pow(Mathf.Max(body.mass,.001f),.25f),.5f,2f);
   var groupWeights=new float[16];foreach(var body in Data.bodies)if(!Pinned(body))groupWeights[body.group]+=Weight(body);
   var groupMass=new float[16];groupMass[4]=.2f;groupMass[5]=.3f;groupMass[6]=.07f;groupMass[7]=.04f;
   groupMass[8]=.2f;groupMass[9]=.55f;groupMass[10]=.1f;''')
s=s.replace('rb.isKinematic=Pinned(d);rb.useGravity=false;rb.mass=Mathf.Clamp(Mathf.Sqrt(d.mass),.04f,5);', '''rb.isKinematic=Pinned(d);rb.useGravity=false;rb.mass=Mathf.Clamp(Mathf.Sqrt(d.mass),.04f,5);
    if(!rb.isKinematic&&groupMass[d.group]>0)rb.mass=groupMass[d.group]*Weight(d)/groupWeights[d.group];''')
s=s.replace('rb.angularDamping=Damping(d.angularDamping);', '''rb.angularDamping=Damping(d.angularDamping);
    if(d.group>=4){rb.linearDamping=Mathf.Min(rb.linearDamping,2.5f);rb.angularDamping=Mathf.Min(rb.angularDamping,3.5f);}''')
changes[p]=s
p=Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs');s=(old/p).read_text(encoding='utf8')
s=s.replace('rb.isKinematic=true;rb.useGravity=false;fingers[h,s]=rb;', '''rb.isKinematic=true;rb.useGravity=false;rb.mass=s==19?.03f:.01f;rb.maxDepenetrationVelocity=.3f;rb.maxAngularVelocity=20;fingers[h,s]=rb;''')
s=s.replace('colliders[h,s].enabled=active;ColliderStateChanges++;', '''colliders[h,s].enabled=active;
   if(!active)fingers[h,s].isKinematic=true;ColliderStateChanges++;''')
s=s.replace('if(!colliders[h,s].enabled){rb.position=p;rb.rotation=q;}', '''if(!colliders[h,s].enabled){rb.position=p;rb.rotation=q;rb.isKinematic=false;rb.linearVelocity=Vector3.zero;rb.angularVelocity=Vector3.zero;}''')
before='''fingers[h,s].MovePosition(Vector3.Lerp(startPosition[h,s],targetPosition[h,s],progress));
     fingers[h,s].MoveRotation(Quaternion.Slerp(startRotation[h,s],targetRotation[h,s],progress));SubstepPoseWrites++;'''
after='''var rb=fingers[h,s];var target=Vector3.Lerp(startPosition[h,s],targetPosition[h,s],progress);
     const float frequency=2*Mathf.PI*10;
     var desiredVelocity=(targetPosition[h,s]-startPosition[h,s])*0; // Position servo deliberately has no tracked-velocity kick.
     var force=rb.mass*(frequency*frequency*(target-rb.position)-2*frequency*(rb.linearVelocity-desiredVelocity));
     rb.AddForce(Vector3.ClampMagnitude(force,s==19?1f:.35f),ForceMode.Force);
     var difference=Quaternion.Slerp(startRotation[h,s],targetRotation[h,s],progress)*Quaternion.Inverse(rb.rotation);
     difference.ToAngleAxis(out float angle,out var axis);if(angle>180)angle-=360;
     var angular=frequency*frequency*angle*Mathf.Deg2Rad*axis.normalized-2*frequency*rb.angularVelocity;
     rb.AddTorque(Vector3.ClampMagnitude(angular,240),ForceMode.Acceleration);SubstepPoseWrites++;'''
assert before in s;s=s.replace(before,after)
# No infinite-mass kinematic hand pushes: contact proxies can yield against constrained cloth.
s=s.replace('40 persistent colliders, substep contact motion and critically damped force-limited grabs;', '40 persistent finite-mass colliders, force-limited substep contact and critically damped grabs;')
changes[p]=s
for rel in ('Assets/MGFR/Scripts/BareHands/HandsReview.cs','Assets/MGFR/Scripts/BareHands/HandRuntimeTiming.cs'):
 p=Path(rel);changes[p]=(old/p).read_text(encoding='utf8')
for p in tuple(changes):changes[p]=changes[p].replace('SubstepPoseWrites','SubstepContactUpdates').replace('substepPoseWrites','substepContactUpdates')
p=Path('Assets/MGFR/Scripts/BareHands/ContactStressReview.cs');s=(old/p).read_text(encoding='utf8')
s=s.replace('int total=360;', '''float hairMass=0,skirtMass=0;for(int i=0;i<physics.Bodies.Length;i++)if(!physics.Bodies[i].isKinematic)
   {if(physics.Data.bodies[i].group==4)hairMass+=physics.Bodies[i].mass;if(physics.Data.bodies[i].group==9)skirtMass+=physics.Bodies[i].mass;}
   int total=360;''')
s=s.replace('contacts={hands.FingerContacts}\\n', 'hairDynamicMassKg={hairMass}\\nskirtDynamicMassKg={skirtMass}\\ncontacts={hands.FingerContacts}\\n')
changes[p]=s
names={p.name for p in changes}
def ignore(path,items):return [n for n in items if n in names]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,new/folder,ignore=ignore)
for p,s in changes.items():
 with (new/p).open('x',encoding='utf8') as f:f.write(s)
print(new)
