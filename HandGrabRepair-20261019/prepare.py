from pathlib import Path
import shutil,hashlib,json,difflib
lab=Path(__file__).resolve().parent
root=Path('H:/MGFR/unity-client')
project=lab/'Project'
assert not project.exists()
base=Path('Assets/MGFR/Scripts/BareHands')
changes={}
def rep(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a))
 return s.replace(a,b)
s=(root/base/'BareHandInteraction.cs').read_text(encoding='utf-8-sig')
s=rep(s,'  HandSurfaceQuery surfaceQuery;', '''  HandSurfaceQuery surfaceQuery;
  readonly List<int> grabbable=new List<int>();Collider[] garmentColliders;
  readonly bool[] acquisitionPending=new bool[2];readonly Vector3[] acquisitionTarget=new Vector3[2];
  public readonly int[] AcquireAttempts=new int[2],AcquireMisses=new int[2];
  public readonly string[] GrabStatus={"等待张手","等待张手"};
  public int PostPhysicsAcquisitions {get;private set;}
  public int ProxyGrabStarts {get;private set;}
  public int SurfaceGrabStarts {get;private set;}''')
s=rep(s,'   surfaceQuery=new HandSurfaceQuery(Physics);', '''   surfaceQuery=new HandSurfaceQuery(Physics);
   for(int i=0;i<Physics.Bodies.Length;i++)
    if(!Physics.Bodies[i].isKinematic&&Physics.Data.bodies[i].group>=4&&Physics.Data.bodies[i].group<=10)grabbable.Add(i);
   garmentColliders=new Collider[grabbable.Count];
   for(int i=0;i<grabbable.Count;i++)garmentColliders[i]=Physics.Bodies[grabbable[i]].GetComponent<Collider>();
   gameObject.AddComponent<HandGrabAcquirePass>().Owner=this;''')
s=s.replace('Release(h);hasAcquire[h]=false;pinchState[h].Reset();','Release(h);acquisitionPending[h]=false;GrabStatus[h]="追踪丢失";hasAcquire[h]=false;pinchState[h].Reset();')
s=s.replace('Release(h);hasAcquire[h]=false;blockedUntilOpen[h]=true;recoveryRemaining[h]=.10f;', 'Release(h);acquisitionPending[h]=false;GrabStatus[h]="位置跳变，张手重置";hasAcquire[h]=false;blockedUntilOpen[h]=true;recoveryRemaining[h]=.10f;')
s=rep(s, '        f.Radius[5]+f.Radius[10]+.020f*f.Scale)blockedUntilOpen[h]=false;', '''        Mathf.Clamp(f.Radius[5]+f.Radius[10],.009f,.032f)+.020f*f.Scale)blockedUntilOpen[h]=false;
     GrabStatus[h]=blockedUntilOpen[h]?"张手重置":"手已张开";''')
s=rep(s,'''    if(pinchState[h].CanAcquire&&!blockedUntilOpen[h]&&recoveryRemaining[h]<=0&&
       Physics.Simulate&&grabs[h]==null&&ballOwner!=h&&acquireDelay[h]<=0)
    {TryGrab(h,target);previousAcquire[h]=f.PinchPoint;hasAcquire[h]=true;acquireDelay[h]=1f/30f;}''', '''    acquisitionPending[h]=pinchState[h].CanAcquire&&!blockedUntilOpen[h]&&recoveryRemaining[h]<=0&&
       Physics.Simulate&&grabs[h]==null&&ballOwner!=h&&acquireDelay[h]<=0;
    acquisitionTarget[h]=target;
    // Manual deterministic reviews disable the automatic physics writer.
    // In a running scene acquisition happens at order 1600, after PhysX (1500)
    // has written the visible garment pose, instead of baking animation-only bones.
    if(!Physics.enabled)AcquireHand(h,false);''')
a=s.index('   var frame=Source.Frames[h];',s.index('  void TryGrab('))
b=s.index('   var body=Physics.Bodies[selected];',a)
s=s[:a]+'''   var frame=Source.Frames[h];AcquireAttempts[h]++;
   float scale=Mathf.Max(.0001f,Mathf.Abs(Physics.Loader.transform.lossyScale.x));
   // Preserve the previous working contact-proxy path. A visible-surface query
   // supplements it when the authored collision proxy sits behind the fabric.
   float reach=Mathf.Clamp(.035f*frame.Scale,.030f,.050f);
   float best=reach/scale;int selected=-1;Vector3 point=target;bool fromSurface=false;
   for(int c=0;c<grabbable.Count;c++)
   {
    int id=grabbable[c];if(id==GrabbedBody[1-h])continue;
    var hit=garmentColliders[c].ClosestPoint(target);
    float score=Vector3.Distance(hit,target)+.04f*Vector3.Distance(Physics.Bodies[id].position,target);
    if(score<best){best=score;selected=id;point=hit;}
   }
   if(selected<0)
   {
    var world=Physics.Loader.transform.TransformPoint(target);
    fromSurface=surfaceQuery.FindSwept(hasAcquire[h]?previousAcquire[h]:world,world,reach,GrabbedBody[1-h],out selected,out point);
   }
   if(selected<0){AcquireMisses[h]++;GrabStatus[h]="捏合已识别，未碰到可抓布料";return;}
   if(fromSurface)SurfaceGrabStarts++;else ProxyGrabStarts++;
   GrabStatus[h]="已抓取 "+Physics.Data.bodies[selected].name;
''' +s[b:]
s=s.replace('Debug.Log($"[MGFR hands] hand={h} cloth grab={Physics.Data.bodies[selected].name}");','Debug.Log($"[MGFR hands] hand={h} cloth grab={Physics.Data.bodies[selected].name} path={(fromSurface?"visible-surface":"physics-proxy")} phase=after-physics");')
s=rep(s,'  void Release(int h)', '''  public void AcquireAfterPhysics()
  {
   if(!IsReady)return;
   for(int h=0;h<2;h++)AcquireHand(h,true);
  }
  void AcquireHand(int h,bool afterPhysics)
  {
   if(!acquisitionPending[h])return;acquisitionPending[h]=false;
   if(afterPhysics)PostPhysicsAcquisitions++;
   TryGrab(h,acquisitionTarget[h]);previousAcquire[h]=Source.Frames[h].PinchPoint;
   hasAcquire[h]=true;acquireDelay[h]=1f/30f;
  }
  void Release(int h)''')
s=rep(s,'   GrabbedBody[h]=-1;breakTime[h]=0;', '   GrabbedBody[h]=-1;breakTime[h]=0;acquisitionPending[h]=false;')
s=rep(s,'observed={Source.Frames[0].ObservedCount},{Source.Frames[1].ObservedCount}";', 'observed={Source.Frames[0].ObservedCount},{Source.Frames[1].ObservedCount} blocked={blockedUntilOpen[0]},{blockedUntilOpen[1]} attempts={AcquireAttempts[0]},{AcquireAttempts[1]} misses={AcquireMisses[0]},{AcquireMisses[1]} proxyGrabs={ProxyGrabStarts} surfaceGrabs={SurfaceGrabStarts} postPhysicsAttempts={PostPhysicsAcquisitions} status={GrabStatus[0]}|{GrabStatus[1]}";')
s=rep(s,'   GUILayout.Label("F8 手部包络 · F9 徒手/手柄 · 捏住后可移向布面");','   GUILayout.Label($"左：{GrabStatus[0]} / 右：{GrabStatus[1]}");')
s=rep(s,' public sealed class RealFingerContact:MonoBehaviour', ''' [DefaultExecutionOrder(1600)]
 public sealed class HandGrabAcquirePass:MonoBehaviour
 {
  public BareHandInteraction Owner;
  void LateUpdate(){if(Owner!=null&&Owner.enabled)Owner.AcquireAfterPhysics();}
 }
 public sealed class RealFingerContact:MonoBehaviour''')
changes[base/'BareHandInteraction.cs']=s
s=(root/base/'HandGrabCoupling.cs').read_text(encoding='utf-8-sig')
s=s.replace('  float age;', '  float age;\n  public float LastForceNewtons {get;private set;}')
s=s.replace('var force=Force(1/inverse,error,relative,dt)*Mathf.Clamp01(age/.06f);', '''// Free-body effective mass can approach zero on long, thin cloth proxies.
   // The cloth joints restrict that rotation, so using it as an unrestricted
   // point mass removed most grip stiffness. Retain at least the legacy mass
   // response while bounding the final force and ramping it in.
   float gripMass=Mathf.Max(1/inverse,Body.mass);
   var force=Force(gripMass,error,relative,dt)*Mathf.Clamp01(age/.035f);
   LastForceNewtons=Mathf.Min(force.magnitude,2.5f);''')
changes[base/'HandGrabCoupling.cs']=s
manifest=[];patch=[]
for p,s in changes.items():
 original=root/p;backup=lab/'Originals'/p;backup.parent.mkdir(parents=True,exist_ok=True)
 with backup.open('xb') as f:f.write(original.read_bytes())
 target=lab/'Candidate'/p;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('x',encoding='utf8') as f:f.write(s)
 manifest.append({'path':str(original),'sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'candidate':str(target)})
 patch.extend(difflib.unified_diff(original.read_text(encoding='utf-8-sig').splitlines(True),s.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix()))
with (lab/'manifest.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2,ensure_ascii=False)
with (lab/'repair.patch').open('x',encoding='utf8') as f:f.writelines(patch)
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(root) in changes]
shutil.copytree(root/'Assets',project/'Assets',ignore=ignore)
shutil.copytree(root/'ProjectSettings',project/'ProjectSettings')
shutil.copytree(Path('H:/MGFR/HandAlgorithm-20261019/Project2/Packages'),project/'Packages')
for p in changes:
 target=project/p;target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write((lab/'Candidate'/p).read_bytes())
print(project)
