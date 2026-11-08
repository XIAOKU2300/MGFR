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
  public bool IsReady {get;private set;}
  public bool PreferBareHands=true,DebugHands;
  public bool OcclusionEnabled=true;
  public readonly bool[] Pinching=new bool[2];
  public readonly int[] GrabbedBody={-1,-1};
  public int FingerContacts {get;private set;}
  public int GrabStarts {get;private set;}
  public PmxSecondaryPhysics Physics {get;private set;}
  public readonly HandDepthMesh[] DepthMeshes=new HandDepthMesh[2];
  public int ActiveColliders {get;private set;}
  ControllerHands controllers;Material material;Transform collisionRoot;
  readonly Rigidbody[,] fingers=new Rigidbody[2,20];readonly Collider[,] colliders=new Collider[2,20];
  readonly Rigidbody[] pinchBodies=new Rigidbody[2];readonly SpringJoint[] grabs=new SpringJoint[2];
  readonly bool[] blockedUntilOpen=new bool[2];readonly Vector3[] previousPalm=new Vector3[2],velocity=new Vector3[2];
  readonly List<int> cloth=new List<int>();Collider[] clothColliders;
  int ballOwner=-1;bool previousTestInput;Font font;string lastStatus="";float nextLog;
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
   Source=gameObject.AddComponent<HandJointSource>();Source.Replay=Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-hand-review")>=0;
   Source.BeforeRenderData+=RefreshDepth;
   material=new Material(Resources.Load<Shader>("HandDepth"));
   collisionRoot=new GameObject("Real finger colliders").transform;
   SceneManager.MoveGameObjectToScene(collisionRoot.gameObject,SceneManager.GetSceneByName("Si isolated PhysX"));
   for(int h=0;h<2;h++)
   {
    DepthMeshes[h]=new HandDepthMesh(h,material);
    for(int s=0;s<20;s++)
    {
     var go=new GameObject($"Real finger {h}:{s}");go.transform.SetParent(collisionRoot,false);
     var rb=go.AddComponent<Rigidbody>();rb.isKinematic=true;rb.useGravity=false;fingers[h,s]=rb;
     colliders[h,s]=s==19?(Collider)go.AddComponent<BoxCollider>():go.AddComponent<CapsuleCollider>();
     colliders[h,s].contactOffset=.001f;colliders[h,s].enabled=false;
     go.AddComponent<RealFingerContact>().Owner=this;
    }
    var pinch=new GameObject("Pinch spring "+h);pinch.transform.SetParent(collisionRoot,false);
    pinchBodies[h]=pinch.AddComponent<Rigidbody>();pinchBodies[h].isKinematic=true;pinchBodies[h].useGravity=false;
   }
   for(int i=0;i<Physics.Data.bodies.Length;i++)
   {
    int group=Physics.Data.bodies[i].group;
    if(!Physics.Bodies[i].isKinematic&&(group==5||group==6||group==7||group==8||group==9||group==10))cloth.Add(i);
   }
   clothColliders=new Collider[cloth.Count];for(int i=0;i<cloth.Count;i++)clothColliders[i]=Physics.Bodies[cloth[i]].GetComponent<Collider>();
   font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",16);IsReady=true;
   Debug.Log("[MGFR hands] Ready: XR Hands 1.8.1, 26 joints/hand, 40 colliders, pinch springs and depth-only hand surfaces. F8 overlay, F9 input source.");
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
    DepthMeshes[h].Update(f,tracked&&OcclusionEnabled);
    for(int s=0;s<20;s++)colliders[h,s].enabled=false;
    if(!tracked)
    {
     Release(h);Pinching[h]=false;blockedUntilOpen[h]=false;previousPalm[h]=Vector3.zero;continue;
    }
    velocity[h]=previousPalm[h]==Vector3.zero?Vector3.zero:Vector3.ClampMagnitude((f.Joints[0].position-previousPalm[h])/Mathf.Max(delta,.0001f),4);
    previousPalm[h]=f.Joints[0].position;
    UpdateColliders(h,f);
    bool old=Pinching[h];float distance=Vector3.Distance(f.Joints[5].position,f.Joints[10].position);
    Pinching[h]=f.Valid[5]&&f.Valid[10]&&distance<(old?.037f:.023f)*f.Scale;
    if(!Pinching[h]){Release(h);blockedUntilOpen[h]=false;}
    var root=Physics.Loader.transform;Vector3 target=root.InverseTransformPoint(f.PinchPoint);
    pinchBodies[h].MovePosition(target);
    if(!old&&Pinching[h]&&!blockedUntilOpen[h]&&Physics.Simulate)TryGrab(h,target);
    if(grabs[h]!=null)
    {
     var body=grabs[h].connectedBody;Vector3 anchor=body.position+body.rotation*grabs[h].connectedAnchor;
     if(!Physics.Simulate||Vector3.Distance(anchor,target)*root.lossyScale.x>.18f){Release(h);blockedUntilOpen[h]=true;}
    }
    if(ballOwner==h)controllers.Ball.position=f.PinchPoint;
   }
  }
  void UpdateColliders(int h,HandFrame f)
  {
   var root=Physics.Loader.transform;float scale=root.lossyScale.x;
   for(int s=0;s<19;s++)
   {
    int a=HandDepthMesh.Segments[s,0],b=HandDepthMesh.Segments[s,1];if(!f.Valid[a]||!f.Valid[b])continue;
    Vector3 pa=root.InverseTransformPoint(f.Joints[a].position),pb=root.InverseTransformPoint(f.Joints[b].position);
    var capsule=(CapsuleCollider)colliders[h,s];capsule.direction=1;
    capsule.radius=Mathf.Clamp((f.Radius[a]+f.Radius[b])*.5f,.005f,.017f)/scale;
    capsule.height=Vector3.Distance(pa,pb)+2*capsule.radius;
    capsule.enabled=true;ActiveColliders++;
    fingers[h,s].MovePosition((pa+pb)*.5f);fingers[h,s].MoveRotation(Quaternion.FromToRotation(Vector3.up,pb-pa));
   }
   HandDepthMesh.PalmShape(f,out var center,out var rotation,out var size);
   var palm=(BoxCollider)colliders[h,19];palm.size=size/scale;palm.enabled=true;ActiveColliders++;
   fingers[h,19].MovePosition(root.InverseTransformPoint(center));fingers[h,19].MoveRotation(Quaternion.Inverse(root.rotation)*rotation);
  }
  void TryGrab(int h,Vector3 target)
  {
   if(ballOwner<0&&Vector3.Distance(Source.Frames[h].PinchPoint,controllers.Ball.position)<.075f)
   {ballOwner=h;controllers.Ball.isKinematic=true;GrabStarts++;return;}
   float scale=Physics.Loader.transform.lossyScale.x,best=.035f/scale;int selected=-1;Vector3 point=target;
   for(int c=0;c<cloth.Count;c++)
   {
    int id=cloth[c];if(id==GrabbedBody[1-h])continue;
    Vector3 closest=clothColliders[c].ClosestPoint(target);
    float distance=Vector3.Distance(closest,target)+.04f*Vector3.Distance(Physics.Bodies[id].position,target);
    if(distance<best){best=distance;selected=id;point=closest;}
   }
   if(selected<0)return;
   // Spring coupling permits stretch and releases on excessive reach; the
   // tracked hand never teleports a skinned cloth bone directly.
   var body=Physics.Bodies[selected];pinchBodies[h].position=target;
   var joint=pinchBodies[h].gameObject.AddComponent<SpringJoint>();joint.autoConfigureConnectedAnchor=false;
   joint.connectedBody=body;joint.anchor=Vector3.zero;joint.connectedAnchor=Quaternion.Inverse(body.rotation)*(point-body.position);
   joint.spring=180;joint.damper=8;joint.minDistance=0;joint.maxDistance=.008f/scale;joint.tolerance=.003f/scale;
   joint.enableCollision=false;grabs[h]=joint;GrabbedBody[h]=selected;GrabStarts++;
   Debug.Log($"[MGFR hands] hand={h} cloth grab={Physics.Data.bodies[selected].name}");
  }
  void Release(int h)
  {
   if(grabs[h]!=null){grabs[h].connectedBody=null;Destroy(grabs[h]);grabs[h]=null;}
   GrabbedBody[h]=-1;
   if(ballOwner==h){controllers.Ball.isKinematic=false;controllers.Ball.linearVelocity=velocity[h];ballOwner=-1;}
  }
  void RefreshDepth()
  {
   if(!IsReady)return;
   for(int h=0;h<2;h++)DepthMeshes[h].Update(Source.Frames[h],PreferBareHands&&OcclusionEnabled);
  }
  void LogStatus()
  {
   if(Time.unscaledTime<nextLog)return;nextLog=Time.unscaledTime+2;
   string state=$"XR_EXT_hand_tracking={Source.ExtensionEnabled} subsystem={Source.Running} source={(Source.Replay?"TEST_REPLAY":"XR_RUNTIME")} left={Source.Frames[0].ValidCount}/26 right={Source.Frames[1].ValidCount}/26 leftPinch={Pinching[0]} rightPinch={Pinching[1]} grab={GrabbedBody[0]},{GrabbedBody[1]} colliders={ActiveColliders}";
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
   GUILayout.Label($"捏合：左 {(Pinching[0]?"合":"开")} / 右 {(Pinching[1]?"合":"开")}    抓布：{(GrabbedBody[0]>=0||GrabbedBody[1]>=0?"抓取中":"无")}");
   if(PreferBareHands&&!Source.Frames[0].Tracked&&!Source.Frames[1].Tracked)GUILayout.Label("等待手部关节：放下手柄，双手举到视野内");
   GUILayout.Label("F8 显示/隐藏手部轮廓 · F9 徒手/手柄");
   GUILayout.EndArea();GUI.skin.font=previous;
  }
  void OnDestroy()
  {
   if(Source!=null)Source.BeforeRenderData-=RefreshDepth;
   if(controllers!=null){Release(0);Release(1);controllers.TestInput=previousTestInput;}
   foreach(var mesh in DepthMeshes)if(mesh!=null){Destroy(mesh.Object);Destroy(mesh.Mesh);}
   if(material!=null)Destroy(material);if(collisionRoot!=null)Destroy(collisionRoot.gameObject);
  }
 }
 public sealed class RealFingerContact:MonoBehaviour
 {
  public BareHandInteraction Owner;
  void OnCollisionEnter(Collision collision){Owner.RecordContact();}
 }
}
