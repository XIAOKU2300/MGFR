using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;
using MGFR.Experience;
using MGFR.PhysicsRig;

namespace MGFR.BareHands
{
 [DefaultExecutionOrder(1300)]
 public sealed class BareHandInteraction:MonoBehaviour
 {
  public HandJointSource Source {get;private set;}
  public Func<int,bool> ExternalClothGrab;
  public bool IsReady {get;private set;}
  public bool PreferBareHands=true,DebugHands;
  public bool OcclusionEnabled=true;
  public readonly bool[] Pinching=new bool[2];
  public readonly int[] GrabbedBody={-1,-1};
  public int FingerContacts {get;private set;}
  public int GrabStarts {get;private set;}
  public int HairGrabStarts {get;private set;}
  public PmxSecondaryPhysics Physics {get;private set;}
  public readonly HandDepthMesh[] DepthMeshes=new HandDepthMesh[2];
  public int ActiveColliders {get;private set;}
  public bool HandProxiesIgnoreEachOther=>IsReady&&UnityEngine.Physics.GetIgnoreCollision(colliders[0,0],colliders[0,19])&&UnityEngine.Physics.GetIgnoreCollision(colliders[0,0],colliders[1,0]);
  ControllerHands controllers;Material material;Transform collisionRoot;
  readonly Rigidbody[,] fingers=new Rigidbody[2,20];readonly Collider[,] colliders=new Collider[2,20];
  readonly Rigidbody[] pinchBodies=new Rigidbody[2];readonly HandGrabCoupling[] grabs=new HandGrabCoupling[2];
  readonly bool[] blockedUntilOpen=new bool[2];readonly Vector3[] previousPalm=new Vector3[2],velocity=new Vector3[2];
  HandSurfaceQuery surfaceQuery;
  readonly List<int> grabbable=new List<int>();Collider[] garmentColliders;
  readonly bool[] acquisitionPending=new bool[2];readonly Vector3[] acquisitionTarget=new Vector3[2];
  public readonly int[] AcquireAttempts=new int[2],AcquireMisses=new int[2];
  public readonly string[] GrabStatus={"等待张手","等待张手"};
  public int PostPhysicsAcquisitions {get;private set;}
  public int ProxyGrabStarts {get;private set;}
  public int SurfaceGrabStarts {get;private set;}
  readonly HandPinchState[] pinchState={new HandPinchState(),new HandPinchState()};
  readonly float[] acquireDelay=new float[2],breakTime=new float[2];
  readonly Vector3[] previousAcquire=new Vector3[2];readonly bool[] hasAcquire=new bool[2];
  readonly Vector3[,] targetPosition=new Vector3[2,20],startPosition=new Vector3[2,20];
  readonly Quaternion[,] targetRotation=new Quaternion[2,20],startRotation=new Quaternion[2,20];
  readonly Vector3[] pinchStart=new Vector3[2],pinchTarget=new Vector3[2];
  public int ColliderStateChanges {get;private set;}public int SubstepContactUpdates {get;private set;}
  PhysicsMaterial contactMaterial;
  int ballOwner=-1;bool previousTestInput;Font font;string lastStatus="";float nextLog;readonly float[] recoveryRemaining=new float[2];
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(SceneManager.GetActiveScene().name!=SiCharacterBootstrap.SceneName||Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-render-review")>=0)return;
   new GameObject("MGFR bare-hand interaction").AddComponent<BareHandInteraction>();
  }
  IEnumerator Start()
  {
   while((Physics=FindAnyObjectByType<PmxSecondaryPhysics>())==null||!Physics.IsReady)yield return null;
   controllers=FindAnyObjectByType<ControllerHands>();previousTestInput=controllers.TestInput;
   // Migration from the old main-project calibration experiment: it installs
   // itself and also owns F10. Preserve its source, but retire the live component.
   foreach(var component in FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
    if(component.GetType().FullName=="MGFR.BareHands.HandAlignment")
    {component.StopAllCoroutines();component.enabled=false;Destroy(component);}
   Source=gameObject.AddComponent<HandJointSource>();Source.Replay=Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-hand-review")>=0;
   Source.BeforeRenderData+=RefreshDepth;
   material=new Material(Resources.Load<Shader>("HandDepth"));
   contactMaterial=new PhysicsMaterial("Sliding real hand contact"){dynamicFriction=.25f,staticFriction=.3f,bounciness=0,frictionCombine=PhysicsMaterialCombine.Minimum,bounceCombine=PhysicsMaterialCombine.Minimum};
   collisionRoot=new GameObject("Real finger colliders").transform;
   SceneManager.MoveGameObjectToScene(collisionRoot.gameObject,SceneManager.GetSceneByName("Si isolated PhysX"));
   for(int h=0;h<2;h++)
   {
    DepthMeshes[h]=new HandDepthMesh(h,material);
    for(int s=0;s<20;s++)
    {
     var go=new GameObject($"Real finger {h}:{s}");go.transform.SetParent(collisionRoot,false);
     var rb=go.AddComponent<Rigidbody>();rb.isKinematic=true;rb.useGravity=false;rb.mass=s==19?.045f:.015f;rb.maxDepenetrationVelocity=.3f;rb.maxAngularVelocity=20;fingers[h,s]=rb;
     rb.collisionDetectionMode=CollisionDetectionMode.ContinuousSpeculative;
     colliders[h,s]=s==19?(Collider)go.AddComponent<BoxCollider>():go.AddComponent<CapsuleCollider>();
     colliders[h,s].contactOffset=.001f;colliders[h,s].sharedMaterial=contactMaterial;colliders[h,s].enabled=false;
     if(s<19)((CapsuleCollider)colliders[h,s]).direction=1;
     go.AddComponent<RealFingerContact>().Owner=this;
    }
    var pinch=new GameObject("Pinch spring "+h);pinch.transform.SetParent(collisionRoot,false);
    pinchBodies[h]=pinch.AddComponent<Rigidbody>();pinchBodies[h].isKinematic=true;pinchBodies[h].useGravity=false;
   }
   surfaceQuery=new HandSurfaceQuery(Physics);
   for(int i=0;i<Physics.Bodies.Length;i++)
    if(!Physics.Bodies[i].isKinematic&&Physics.Data.bodies[i].group>=4&&Physics.Data.bodies[i].group<=10)grabbable.Add(i);
   garmentColliders=new Collider[grabbable.Count];
   for(int i=0;i<grabbable.Count;i++)garmentColliders[i]=Physics.Bodies[grabbable[i]].GetComponent<Collider>();
   gameObject.AddComponent<HandGrabAcquirePass>().Owner=this;
   // Adjacent fingers and palms overlap by design. They must not fight
   // each other before their limited force can reach the garment.
   for(int a=0;a<40;a++)for(int b=a+1;b<40;b++)
    UnityEngine.Physics.IgnoreCollision(colliders[a/20,a%20],colliders[b/20,b%20],true);
   font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",16);IsReady=true;
   Physics.BeforeSubstep+=MoveContacts;gameObject.AddComponent<HandRuntimeTiming>();
   Debug.Log("[MGFR hands] Ready: XR Hands 1.8.1, 26 joints/hand, 40 persistent finite-mass colliders, force-limited substep contact and surface-based reacquisition, anatomical depth envelope and implicit damped grabs; no visual extrapolation. F8 overlay, F9 input source.");
  }
  void LateUpdate()
  {
   if(!IsReady)return;
   if(Input.GetKeyDown(KeyCode.F8))DebugHands=!DebugHands;
   if(Input.GetKeyDown(KeyCode.F9)){PreferBareHands=!PreferBareHands;Release(0);Release(1);}
   StepInteraction(Time.deltaTime);LogStatus();
  }
  public void StepInteraction(float delta)
  {
   controllers.TestInput=PreferBareHands||previousTestInput;ActiveColliders=0;
   material.SetFloat("_WriteColor",DebugHands?15:0);
   for(int h=0;h<2;h++)
   {
    var f=Source.Frames[h];bool tracked=PreferBareHands&&f.Tracked;
    if(PreferBareHands)
    {
     controllers.Hands[h].Active=false;controllers.Hands[h].Grip=false;controllers.Hands[h].Palm.gameObject.SetActive(false);
    }
    if(Source.Replay||!Source.Running||!tracked)DepthMeshes[h].Update(Source.RenderFrames[h],tracked&&OcclusionEnabled);
    if(!tracked)
    {
     for(int s=0;s<20;s++)SetColliderState(h,s,false);
     Release(h);acquisitionPending[h]=false;GrabStatus[h]="追踪丢失";hasAcquire[h]=false;pinchState[h].Reset();Pinching[h]=false;blockedUntilOpen[h]=true;previousPalm[h]=Vector3.zero;continue;
    }
    if(previousPalm[h]!=Vector3.zero&&Vector3.Distance(f.Joints[0].position,previousPalm[h])>.18f)
    {
     Release(h);acquisitionPending[h]=false;GrabStatus[h]="位置跳变，张手重置";hasAcquire[h]=false;blockedUntilOpen[h]=true;recoveryRemaining[h]=.10f;
     for(int s=0;s<20;s++)SetColliderState(h,s,false);
    }
    velocity[h]=previousPalm[h]==Vector3.zero?Vector3.zero:Vector3.ClampMagnitude((f.Joints[0].position-previousPalm[h])/Mathf.Max(delta,.0001f),4);
    previousPalm[h]=f.Joints[0].position;
    recoveryRemaining[h]=Mathf.Max(0,recoveryRemaining[h]-delta);
    if(recoveryRemaining[h]<=0)UpdateColliders(h,f);
    Pinching[h]=pinchState[h].Update(f,delta);
    if(!Pinching[h])
    {
     Release(h);hasAcquire[h]=false;
     // A predicted/held tip is not evidence that the user opened their hand.
     if(f.CanStartPinch&&Vector3.Distance(f.Joints[5].position,f.Joints[10].position)>
        Mathf.Clamp(f.Radius[5]+f.Radius[10],.009f,.032f)+.020f*f.Scale)blockedUntilOpen[h]=false;
     GrabStatus[h]=blockedUntilOpen[h]?"张手重置":"手已张开";
    }
    var root=Physics.Loader.transform;Vector3 target=root.InverseTransformPoint(f.PinchPoint);
    pinchStart[h]=pinchBodies[h].position;pinchTarget[h]=target;
    acquireDelay[h]=Mathf.Max(0,acquireDelay[h]-delta);
    acquisitionPending[h]=pinchState[h].CanAcquire&&!blockedUntilOpen[h]&&recoveryRemaining[h]<=0&&
       Physics.Simulate&&grabs[h]==null&&ballOwner!=h&&acquireDelay[h]<=0;
    acquisitionTarget[h]=target;
    // Manual deterministic reviews disable the automatic physics writer.
    // In a running scene acquisition happens at order 1600, after PhysX (1500)
    // has written the visible garment pose, instead of baking animation-only bones.
    if(!Physics.enabled)AcquireHand(h,false);
    if(grabs[h]!=null)
    {
     var body=grabs[h].Body;Vector3 anchor=body.position+body.rotation*grabs[h].LocalAnchor;
     float error=Vector3.Distance(anchor,grabs[h].Target(target))*Mathf.Abs(root.lossyScale.x);
     breakTime[h]=error>.12f?breakTime[h]+delta:0;
     if(!Physics.Simulate||breakTime[h]>.12f||error>.30f){Release(h);blockedUntilOpen[h]=true;}
    }
    if(ballOwner==h)controllers.Ball.position=f.PinchPoint;
   }
   // More substeps only near the model, not whenever a hand is tracked.
   var bounds=Physics.Loader.Renderer.bounds;bounds.Expand(.30f);
   Physics.PreciseContacts=ActiveColliders>0&&
    ((Source.Frames[0].Tracked&&bounds.Contains(Source.Frames[0].PinchPoint))||
     (Source.Frames[1].Tracked&&bounds.Contains(Source.Frames[1].PinchPoint)));
  }
  void UpdateColliders(int h,HandFrame f)
  {
   var root=Physics.Loader.transform;float scale=root.lossyScale.x;
   for(int s=0;s<19;s++)
   {
    int a=HandDepthMesh.Segments[s,0],b=HandDepthMesh.Segments[s,1];
    if(!f.Valid[a]||!f.Valid[b]){SetColliderState(h,s,false);continue;}
    Vector3 pa=root.InverseTransformPoint(f.Joints[a].position),pb=root.InverseTransformPoint(f.Joints[b].position);
    var capsule=(CapsuleCollider)colliders[h,s];
    float radius=Mathf.Clamp((f.Radius[a]+f.Radius[b])*.5f,.004f,.025f)/scale;
    float height=Vector3.Distance(pa,pb)+2*radius;
    if(Mathf.Abs(capsule.radius-radius)>.0005f/scale)capsule.radius=radius;
    if(Mathf.Abs(capsule.height-height)>.0005f/scale)capsule.height=height;
    SetContactTarget(h,s,(pa+pb)*.5f,Quaternion.FromToRotation(Vector3.up,pb-pa));ActiveColliders++;
   }
   HandDepthMesh.PalmShape(f,out var center,out var rotation,out var size);
   var palm=(BoxCollider)colliders[h,19];if((palm.size-size/scale).sqrMagnitude>.00000025f/(scale*scale))palm.size=size/scale;
   SetContactTarget(h,19,root.InverseTransformPoint(center),Quaternion.Inverse(root.rotation)*rotation);ActiveColliders++;
  }
  void SetColliderState(int h,int s,bool active)
  {
   if(colliders[h,s].enabled==active)return;
   colliders[h,s].enabled=active;
   if(!active)fingers[h,s].isKinematic=true;ColliderStateChanges++;
  }
  void SetContactTarget(int h,int s,Vector3 p,Quaternion q)
  {
   var rb=fingers[h,s];
   if(!colliders[h,s].enabled){rb.position=p;rb.rotation=q;rb.isKinematic=false;rb.linearVelocity=Vector3.zero;rb.angularVelocity=Vector3.zero;}
   startPosition[h,s]=rb.position;startRotation[h,s]=rb.rotation;targetPosition[h,s]=p;targetRotation[h,s]=q;
   SetColliderState(h,s,true);
  }
  void MoveContacts(float dt,float progress)
  {
   for(int h=0;h<2;h++)
   {
    for(int s=0;s<20;s++)if(colliders[h,s].enabled)
    {
     var rb=fingers[h,s];var target=Vector3.Lerp(startPosition[h,s],targetPosition[h,s],progress);
     const float frequency=2*Mathf.PI*12;
     float modelScale=Mathf.Max(.0001f,Mathf.Abs(Physics.Loader.transform.lossyScale.x));
     var feed=Vector3.ClampMagnitude(velocity[h]/modelScale,2/modelScale);
     var force=rb.mass*(frequency*frequency*(target-rb.position)-2*frequency*(rb.linearVelocity-feed));
     rb.AddForce(Vector3.ClampMagnitude(force,s==19?1.5f:.60f),ForceMode.Force);
     var difference=Quaternion.Slerp(startRotation[h,s],targetRotation[h,s],progress)*Quaternion.Inverse(rb.rotation);
     difference.ToAngleAxis(out float angle,out var axis);if(angle>180)angle-=360;
     var angular=frequency*frequency*angle*Mathf.Deg2Rad*axis.normalized-2*frequency*rb.angularVelocity;
     rb.AddTorque(Vector3.ClampMagnitude(angular,240),ForceMode.Acceleration);SubstepContactUpdates++;
    }
    var point=Vector3.Lerp(pinchStart[h],pinchTarget[h],progress);pinchBodies[h].MovePosition(point);
    if(grabs[h]!=null)grabs[h].Step(point,dt);
   }
  }
  void TryGrab(int h,Vector3 target)
  {
   if(ballOwner<0&&Vector3.Distance(Source.Frames[h].PinchPoint,controllers.Ball.position)<.075f)
   {ballOwner=h;controllers.Ball.isKinematic=true;GrabStarts++;return;}
   var frame=Source.Frames[h];AcquireAttempts[h]++;
   float scale=Mathf.Max(.0001f,Mathf.Abs(Physics.Loader.transform.lossyScale.x));
   // Preserve the previous working contact-proxy path. A visible-surface query
   // supplements it when the authored collision proxy sits behind the fabric.
   float reach=Mathf.Clamp(.035f*frame.Scale,.030f,.050f);
   float best=reach/scale;int selected=-1;Vector3 point=target;bool fromSurface=false;
   for(int c=0;c<grabbable.Count;c++)
   {
    int id=grabbable[c];if(id==GrabbedBody[1-h]||!garmentColliders[c].enabled)continue;
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
   var body=Physics.Bodies[selected];pinchBodies[h].position=target;pinchStart[h]=target;
   var grab=pinchBodies[h].gameObject.AddComponent<HandGrabCoupling>();grab.Body=body;
   grab.LocalAnchor=Quaternion.Inverse(body.rotation)*(point-body.position);
   grab.TargetOffset=point-target;grab.PreviousTarget=point;grab.Surface=body.GetComponent<Collider>();
   breakTime[h]=0;
   grabs[h]=grab;GrabbedBody[h]=selected;GrabStarts++;
   if(Physics.Data.bodies[selected].name.Contains("hair")||Physics.Data.bodies[selected].name.Contains("strand"))HairGrabStarts++;
   for(int s=0;s<20;s++)UnityEngine.Physics.IgnoreCollision(colliders[h,s],grab.Surface,true);
   Debug.Log($"[MGFR hands] hand={h} cloth grab={Physics.Data.bodies[selected].name} path={(fromSurface?"visible-surface":"physics-proxy")} phase=after-physics");
  }
  public void AcquireAfterPhysics()
  {
   if(!IsReady)return;
   for(int h=0;h<2;h++)AcquireHand(h,true);
  }
  void AcquireHand(int h,bool afterPhysics)
  {
   if(ExternalClothGrab!=null&&ExternalClothGrab(h))
   {Release(h);blockedUntilOpen[h]=true;GrabStatus[h]="泳装布料抓取中";return;}
   if(!acquisitionPending[h])return;acquisitionPending[h]=false;
   if(afterPhysics)PostPhysicsAcquisitions++;
   TryGrab(h,acquisitionTarget[h]);previousAcquire[h]=Source.Frames[h].PinchPoint;
   hasAcquire[h]=true;acquireDelay[h]=1f/30f;
  }
  public int SkinSurfaceTriangles=>surfaceQuery!=null?surfaceQuery.EligibleTriangles:0;
  public void PrepareSkinChange()
  {
   if(!IsReady)return;
   for(int h=0;h<2;h++)
   {
    Release(h);pinchState[h].Reset();Pinching[h]=false;blockedUntilOpen[h]=true;
    recoveryRemaining[h]=.12f;hasAcquire[h]=false;previousPalm[h]=Vector3.zero;
    for(int s=0;s<20;s++)SetColliderState(h,s,false);
   }
  }
  public void RebuildSkinSurface()
  {
   if(surfaceQuery!=null)surfaceQuery.Dispose();
   surfaceQuery=new HandSurfaceQuery(Physics);
  }
  void Release(int h)
  {
   if(grabs[h]!=null)
   {
    for(int s=0;s<20;s++)UnityEngine.Physics.IgnoreCollision(colliders[h,s],grabs[h].Surface,false);
    Destroy(grabs[h]);grabs[h]=null;
   }
   GrabbedBody[h]=-1;breakTime[h]=0;acquisitionPending[h]=false;
   if(ballOwner==h){controllers.Ball.isKinematic=false;controllers.Ball.linearVelocity=velocity[h];ballOwner=-1;}
  }
  void RefreshDepth()
  {
   if(!IsReady)return;
   for(int h=0;h<2;h++)DepthMeshes[h].Update(Source.RenderFrames[h],PreferBareHands&&OcclusionEnabled);
  }
  void LogStatus()
  {
   if(Time.unscaledTime<nextLog)return;nextLog=Time.unscaledTime+2;
   string state=$"XR_EXT_hand_tracking={Source.ExtensionEnabled} subsystem={Source.Running} source={(Source.Replay?"TEST_REPLAY":"XR_RUNTIME")} left={Source.Frames[0].ValidCount}/26 right={Source.Frames[1].ValidCount}/26 leftPinch={Pinching[0]} rightPinch={Pinching[1]} grab={GrabbedBody[0]},{GrabbedBody[1]} colliders={ActiveColliders} observed={Source.Frames[0].ObservedCount},{Source.Frames[1].ObservedCount} blocked={blockedUntilOpen[0]},{blockedUntilOpen[1]} attempts={AcquireAttempts[0]},{AcquireAttempts[1]} misses={AcquireMisses[0]},{AcquireMisses[1]} proxyGrabs={ProxyGrabStarts} surfaceGrabs={SurfaceGrabStarts} postPhysicsAttempts={PostPhysicsAcquisitions} status={GrabStatus[0]}|{GrabStatus[1]}";
   if(state!=lastStatus){Debug.Log("[MGFR hands] "+state);lastStatus=state;}
  }
  public void RecordContact(){FingerContacts++;}
  void OnGUI()
  {
   if(!IsReady)return;
   var previous=GUI.skin.font;if(font!=null)GUI.skin.font=font;
   GUILayout.BeginArea(new Rect(Screen.width-415,Screen.height-205,402,190),GUI.skin.box);
   GUILayout.Label(Source.Replay?"手部回放测试（非头显实测）":PreferBareHands?"徒手交互":"手柄交互");
   GUILayout.Label($"左手 {Source.Frames[0].ValidCount}/26    右手 {Source.Frames[1].ValidCount}/26");
   GUILayout.Label($"捏合：左 {(Pinching[0]?"合":"开")} / 右 {(Pinching[1]?"合":"开")}    抓布：{(GrabbedBody[0]>=0||GrabbedBody[1]>=0||(ExternalClothGrab!=null&&(ExternalClothGrab(0)||ExternalClothGrab(1)))?"抓取中":"无")}");
   if(PreferBareHands&&!Source.Frames[0].Tracked&&!Source.Frames[1].Tracked)GUILayout.Label("等待手部关节：放下手柄，双手举到视野内");
   GUILayout.Label($"左：{GrabStatus[0]} / 右：{GrabStatus[1]}");
   GUILayout.EndArea();GUI.skin.font=previous;
  }
  void OnDestroy()
  {
   if(Source!=null)Source.BeforeRenderData-=RefreshDepth;
   if(Physics!=null)Physics.BeforeSubstep-=MoveContacts;
   if(controllers!=null){Release(0);Release(1);controllers.TestInput=previousTestInput;}
   if(surfaceQuery!=null)surfaceQuery.Dispose();
   foreach(var mesh in DepthMeshes)if(mesh!=null){mesh.DisposeEnvelope();Destroy(mesh.Object);Destroy(mesh.Mesh);}
   if(contactMaterial!=null)Destroy(contactMaterial);if(material!=null)Destroy(material);if(collisionRoot!=null)Destroy(collisionRoot.gameObject);
  }
 }
 [DefaultExecutionOrder(1600)]
 public sealed class HandGrabAcquirePass:MonoBehaviour
 {
  public BareHandInteraction Owner;
  void LateUpdate(){if(Owner!=null&&Owner.enabled)Owner.AcquireAfterPhysics();}
 }
 public sealed class RealFingerContact:MonoBehaviour
 {
  public BareHandInteraction Owner;
  void OnCollisionEnter(Collision collision){Owner.RecordContact();}
 }
}
