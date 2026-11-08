from pathlib import Path
import shutil

lab=Path('H:/MGFR/HandLab-20261018')
old=lab/'Project-v9'; project=lab/'Project-v11'; source=lab/'Sources/v11'
assert not project.exists(), 'Use a fresh project directory'

def replace(text, before, after):
    assert before in text, before[:120]
    return text.replace(before, after)

def emit(name,text):
    with (source/name).open('x',encoding='utf8') as f:f.write(text)

p=old/'Assets/MGFR/Scripts/BareHands/HandJointSource.cs'
s=p.read_text(encoding='utf8')
s=replace(s,'Transform origin;float nextScan;', 'Transform origin;float nextScan;\n  public int PhysicsSamples,DynamicCallbacks,RenderCallbacks,TrackingLosses,MissingUpdates;')
s=replace(s,'for(int h=0;h<2;h++)if(!Running||Time.unscaledTime-Frames[h].Timestamp>.1f){Frames[h].Clear();RenderFrames[h].Clear();filters[h].Reset();}', '''for(int h=0;h<2;h++)
   {
    if(!Running||Time.unscaledTime-Frames[h].Timestamp>.1f){Frames[h].Clear();filters[h].Reset();}
    if(!Running||Time.unscaledTime-RenderFrames[h].Timestamp>.1f)RenderFrames[h].Clear();
   }''')
s=replace(s,'Read(0,s.leftHand,Frames[0],(flags&XRHandSubsystem.UpdateSuccessFlags.LeftHandJoints)!=0);','if(type==XRHandSubsystem.UpdateType.Dynamic)DynamicCallbacks++;else RenderCallbacks++;\n   Read(0,s.leftHand,Frames[0],(flags&XRHandSubsystem.UpdateSuccessFlags.LeftHandJoints)!=0,type);')
s=replace(s,'Read(1,s.rightHand,Frames[1],(flags&XRHandSubsystem.UpdateSuccessFlags.RightHandJoints)!=0);','Read(1,s.rightHand,Frames[1],(flags&XRHandSubsystem.UpdateSuccessFlags.RightHandJoints)!=0,type);')
s=replace(s,'void Read(int h,XRHand hand,HandFrame f,bool updated)','void Read(int h,XRHand hand,HandFrame f,bool updated,XRHandSubsystem.UpdateType type)')
s=replace(s,'if(!hand.isTracked){f.Clear();RenderFrames[h].Clear();filters[h].Reset();return;}\n   if(!updated)return;', '''if(!hand.isTracked){if(f.Tracked||RenderFrames[h].Tracked)TrackingLosses++;f.Clear();RenderFrames[h].Clear();filters[h].Reset();return;}
   if(!updated){MissingUpdates++;return;}''')
s=replace(s,'filters[h].Process(raw,f,Time.realtimeSinceStartupAsDouble);\n   UpdateRenderFrame(h,raw,f);', '''AcceptSample(h,raw,type,Time.realtimeSinceStartupAsDouble);
  }
  public void AcceptSample(int h,HandFrame sample,XRHandSubsystem.UpdateType type,double now)
  {
   if(type==XRHandSubsystem.UpdateType.Dynamic){filters[h].Process(sample,Frames[h],now);PhysicsSamples++;}
   UpdateRenderFrame(h,sample,Frames[h]);''')
emit('HandJointSource.cs',s)

p=old/'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs';s=p.read_text(encoding='utf8')
s=replace(s,'readonly SpringJoint[] grabs=new SpringJoint[2];', 'readonly HandGrabCoupling[] grabs=new HandGrabCoupling[2];')
s=replace(s,'int ballOwner=-1;', '''readonly Vector3[,] targetPosition=new Vector3[2,20],startPosition=new Vector3[2,20];
  readonly Quaternion[,] targetRotation=new Quaternion[2,20],startRotation=new Quaternion[2,20];
  readonly Vector3[] pinchStart=new Vector3[2],pinchTarget=new Vector3[2];
  public int ColliderStateChanges {get;private set;}public int SubstepPoseWrites {get;private set;}
  PhysicsMaterial contactMaterial;
  int ballOwner=-1;''')
s=replace(s,'material=new Material(Resources.Load<Shader>("HandDepth"));','''material=new Material(Resources.Load<Shader>("HandDepth"));
   contactMaterial=new PhysicsMaterial("Sliding real hand contact"){dynamicFriction=.25f,staticFriction=.3f,bounciness=0,frictionCombine=PhysicsMaterialCombine.Minimum,bounceCombine=PhysicsMaterialCombine.Minimum};''')
s=replace(s,'colliders[h,s].contactOffset=.001f;colliders[h,s].enabled=false;','''colliders[h,s].contactOffset=.001f;colliders[h,s].sharedMaterial=contactMaterial;colliders[h,s].enabled=false;
     if(s<19)((CapsuleCollider)colliders[h,s]).direction=1;''')
s=replace(s,'font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",16);IsReady=true;','''font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",16);IsReady=true;
   Physics.BeforeSubstep+=MoveContacts;gameObject.AddComponent<HandRuntimeTiming>();''')
s=replace(s,'40 colliders, pinch springs and depth-only hand surfaces.', '40 persistent colliders, substep contact motion and critically damped force-limited grabs; no visual extrapolation.')
s=replace(s,'DepthMeshes[h].Update(Source.RenderFrames[h],tracked&&OcclusionEnabled);\n    for(int s=0;s<20;s++)colliders[h,s].enabled=false;', '''if(Source.Replay||!Source.Running)DepthMeshes[h].Update(Source.RenderFrames[h],tracked&&OcclusionEnabled);''')
s=replace(s,'Release(h);Pinching[h]=false;blockedUntilOpen[h]=false;previousPalm[h]=Vector3.zero;continue;', '''for(int s=0;s<20;s++)SetColliderState(h,s,false);
     Release(h);Pinching[h]=false;blockedUntilOpen[h]=true;previousPalm[h]=Vector3.zero;continue;''')
s=replace(s,'velocity[h]=previousPalm[h]==Vector3.zero?', '''if(previousPalm[h]!=Vector3.zero&&Vector3.Distance(f.Joints[0].position,previousPalm[h])>.18f)
    {
     Release(h);blockedUntilOpen[h]=true;
     for(int s=0;s<20;s++)SetColliderState(h,s,false);
    }
    velocity[h]=previousPalm[h]==Vector3.zero?''')
s=replace(s,'pinchBodies[h].MovePosition(target);','pinchStart[h]=pinchBodies[h].position;pinchTarget[h]=target;')
s=replace(s,'var body=grabs[h].connectedBody;Vector3 anchor=body.position+body.rotation*grabs[h].connectedAnchor;', 'var body=grabs[h].Body;Vector3 anchor=body.position+body.rotation*grabs[h].LocalAnchor;')
s=replace(s,'int a=HandDepthMesh.Segments[s,0],b=HandDepthMesh.Segments[s,1];if(!f.Valid[a]||!f.Valid[b])continue;', '''int a=HandDepthMesh.Segments[s,0],b=HandDepthMesh.Segments[s,1];
    if(!f.Valid[a]||!f.Valid[b]){SetColliderState(h,s,false);continue;}''')
s=replace(s,'var capsule=(CapsuleCollider)colliders[h,s];capsule.direction=1;\n    capsule.radius=Mathf.Clamp((f.Radius[a]+f.Radius[b])*.5f,.005f,.017f)/scale;\n    capsule.height=Vector3.Distance(pa,pb)+2*capsule.radius;\n    capsule.enabled=true;ActiveColliders++;\n    fingers[h,s].MovePosition((pa+pb)*.5f);fingers[h,s].MoveRotation(Quaternion.FromToRotation(Vector3.up,pb-pa));', '''var capsule=(CapsuleCollider)colliders[h,s];
    float radius=Mathf.Clamp((f.Radius[a]+f.Radius[b])*.5f,.005f,.017f)/scale;
    float height=Vector3.Distance(pa,pb)+2*radius;
    if(Mathf.Abs(capsule.radius-radius)>.0005f/scale)capsule.radius=radius;
    if(Mathf.Abs(capsule.height-height)>.0005f/scale)capsule.height=height;
    SetContactTarget(h,s,(pa+pb)*.5f,Quaternion.FromToRotation(Vector3.up,pb-pa));ActiveColliders++;''')
s=replace(s,'var palm=(BoxCollider)colliders[h,19];palm.size=size/scale;palm.enabled=true;ActiveColliders++;\n   fingers[h,19].MovePosition(root.InverseTransformPoint(center));fingers[h,19].MoveRotation(Quaternion.Inverse(root.rotation)*rotation);', '''var palm=(BoxCollider)colliders[h,19];if((palm.size-size/scale).sqrMagnitude>.00000025f/(scale*scale))palm.size=size/scale;
   SetContactTarget(h,19,root.InverseTransformPoint(center),Quaternion.Inverse(root.rotation)*rotation);ActiveColliders++;
  }
  void SetColliderState(int h,int s,bool active)
  {
   if(colliders[h,s].enabled==active)return;
   colliders[h,s].enabled=active;ColliderStateChanges++;
  }
  void SetContactTarget(int h,int s,Vector3 p,Quaternion q)
  {
   var rb=fingers[h,s];
   if(!colliders[h,s].enabled){rb.position=p;rb.rotation=q;}
   startPosition[h,s]=rb.position;startRotation[h,s]=rb.rotation;targetPosition[h,s]=p;targetRotation[h,s]=q;
   SetColliderState(h,s,true);
  }
  void MoveContacts(float dt,float progress)
  {
   for(int h=0;h<2;h++)
   {
    for(int s=0;s<20;s++)if(colliders[h,s].enabled)
    {
     fingers[h,s].MovePosition(Vector3.Lerp(startPosition[h,s],targetPosition[h,s],progress));
     fingers[h,s].MoveRotation(Quaternion.Slerp(startRotation[h,s],targetRotation[h,s],progress));SubstepPoseWrites++;
    }
    var point=Vector3.Lerp(pinchStart[h],pinchTarget[h],progress);pinchBodies[h].MovePosition(point);
    if(grabs[h]!=null)grabs[h].Step(point,dt);
   }''')
s=replace(s,'float scale=Physics.Loader.transform.lossyScale.x,best=.035f/scale;int selected=-1;Vector3 point=target;', 'float scale=Physics.Loader.transform.lossyScale.x,best=.035f/scale;int selected=-1,selectedCollider=-1;Vector3 point=target;')
s=replace(s,'selected=id;point=closest;', 'selected=id;selectedCollider=c;point=closest;')
a=s.index('   // Spring coupling permits stretch');b=s.index('   Debug.Log($"[MGFR hands] hand={h} cloth grab=',a)
s=s[:a]+'''   var body=Physics.Bodies[selected];pinchBodies[h].position=target;pinchStart[h]=target;
   var grab=pinchBodies[h].gameObject.AddComponent<HandGrabCoupling>();grab.Body=body;
   grab.LocalAnchor=Quaternion.Inverse(body.rotation)*(point-body.position);grab.PreviousTarget=target;grab.Surface=clothColliders[selectedCollider];
   grabs[h]=grab;GrabbedBody[h]=selected;GrabStarts++;
   for(int s=0;s<20;s++)UnityEngine.Physics.IgnoreCollision(colliders[h,s],grab.Surface,true);
''' + s[b:]
s=replace(s,'if(grabs[h]!=null){grabs[h].connectedBody=null;Destroy(grabs[h]);grabs[h]=null;}', '''if(grabs[h]!=null)
   {
    for(int s=0;s<20;s++)UnityEngine.Physics.IgnoreCollision(colliders[h,s],grabs[h].Surface,false);
    Destroy(grabs[h]);grabs[h]=null;
   }''')
s=replace(s,'if(Source!=null)Source.BeforeRenderData-=RefreshDepth;', '''if(Source!=null)Source.BeforeRenderData-=RefreshDepth;
   if(Physics!=null)Physics.BeforeSubstep-=MoveContacts;''')
s=replace(s,'if(material!=null)Destroy(material);', 'if(contactMaterial!=null)Destroy(contactMaterial);if(material!=null)Destroy(material);')
emit('BareHandInteraction.cs',s)

p=old/'Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs';s=p.read_text(encoding='utf8')
s=replace(s,'public float LastMilliseconds {get;private set;}', 'public float LastMilliseconds {get;private set;}\n  public event Action<float,float> BeforeSubstep;')
s=replace(s,'var timer=System.Diagnostics.Stopwatch.StartNew();RestoreAnimatedBones();', 'long started=System.Diagnostics.Stopwatch.GetTimestamp();RestoreAnimatedBones();')
s=replace(s,'if(!Simulate)return;', 'if(!Simulate){LastMilliseconds=0;return;}')
s=replace(s,'accumulator+=Mathf.Min(delta,.05f);\n   while(accumulator>=Step)\n   {', '''accumulator+=Mathf.Min(delta,.05f);
   int count=Mathf.FloorToInt(accumulator/Step),step=0;
   while(accumulator>=Step)
   {
    BeforeSubstep?.Invoke(Step,++step/(float)count);''')
s=replace(s,'timer.Stop();LastMilliseconds=(float)timer.Elapsed.TotalMilliseconds;', 'LastMilliseconds=(float)((System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000d/System.Diagnostics.Stopwatch.Frequency);')
emit('PmxSecondaryPhysics.cs',s)

p=old/'Assets/MGFR/Scripts/BareHands/HandDepthMesh.cs';s=p.read_text(encoding='utf8')
s=replace(s,'double lastFit;', 'double lastFit;int lastLayer=-1;')
s=replace(s,'Object.SetActive(show&&f.Tracked);if(!Object.activeSelf)return;', 'bool active=show&&f.Tracked;if(Object.activeSelf!=active)Object.SetActive(active);if(!active)return;')
s=replace(s,'foreach(var child in hierarchy)child.gameObject.layer=Object.layer;', 'if(lastLayer!=Object.layer){lastLayer=Object.layer;foreach(var child in hierarchy)child.gameObject.layer=lastLayer;}')
emit('HandDepthMesh.cs',s)

p=old/'Assets/MGFR/Scripts/BareHands/HandsReview.cs';s=p.read_text(encoding='utf8')
s=replace(s,'bool both=hands.ActiveColliders==40;', '''bool both=hands.ActiveColliders==40;
   int toggles=hands.ColliderStateChanges;for(int repeat=0;repeat<4;repeat++)hands.StepInteraction(1f/60f);
   bool persistent=hands.ColliderStateChanges==toggles;''')
s=replace(s,'bool pass=both&&oneLost', 'bool pass=persistent&&both&&oneLost')
s=replace(s,'source=TEST_REPLAY_NOT_HEADSET\\n', 'source=TEST_REPLAY_NOT_HEADSET\\npersistentColliderState={persistent}\\nsubstepPoseWrites={hands.SubstepPoseWrites}\\n')
emit('HandsReview.cs',s)

destinations={
 'PmxSecondaryPhysics.cs':'Scripts/PhysicsRig',
 'ContinuousHandsBuild.cs':'Editor',
}
changed={p.name for p in source.iterdir() if p.suffix=='.cs'}
def ignore(path,names):
 return [name for name in names if name in changed and (Path(path).name in ('BareHands','PhysicsRig','Editor'))]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for p in source.iterdir():
 if p.suffix!='.cs':continue
 target=project/'Assets/MGFR'/destinations.get(p.name,'Scripts/BareHands')/p.name
 with p.open('rb') as r,target.open('xb') as w:shutil.copyfileobj(r,w)
print(project)
