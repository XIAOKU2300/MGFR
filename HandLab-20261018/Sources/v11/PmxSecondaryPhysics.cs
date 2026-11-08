using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;
using MGFR.Experience;

namespace MGFR.PhysicsRig
{
 [Serializable] public sealed class BodyData
 {
  public string name;public int index,bone,group,mask,shape,mode;
  public float[] size,position,rotation;
  public float mass,linearDamping,angularDamping,restitution,friction;
 }
 [Serializable] public sealed class JointData
 {
  public string name;public int kind,a,b;
  public float[] position,rotation,linearLower,linearUpper,angularLower,angularUpper,linearSpring,angularSpring;
 }
 [Serializable] public sealed class PhysicsData {public BodyData[] bodies;public JointData[] joints;}

 // Native PhysX spring joints drive the actual skinned bones. Simulation uses
 // model metres in an isolated scene, independent of the character's UI scale.
 [DefaultExecutionOrder(1500)]
 public sealed class PmxSecondaryPhysics:MonoBehaviour
 {
  public bool IsReady {get;private set;}
  public bool Simulate=true;
  public Rigidbody[] Bodies {get;private set;}
  public readonly List<ConfigurableJoint> Joints=new List<ConfigurableJoint>();
  public PhysicsData Data {get;private set;}
  public SiCharacterLoader Loader {get;private set;}
  public int DynamicCount {get;private set;}
  public float LastMilliseconds {get;private set;}
  public event Action<float,float> BeforeSubstep;
  public int Contacts {get;private set;}
  Scene scene;PhysicsScene world;Transform container;Transform[] rig;
  Collider[] colliders;Rigidbody[] palms=new Rigidbody[2];SphereCollider[] palmColliders=new SphereCollider[2];
  Vector3[] offsets,localRest,modelTargets;Quaternion[] restRotations;int[] order;
  ControllerHands hands;Vector3 lastRoot,lastVelocity;float accumulator;
  const float Step=1f/120f;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(SceneManager.GetActiveScene().name!=SiCharacterBootstrap.SceneName)return;
   if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-render-review")>=0)return;
   new GameObject("Si full secondary physics").AddComponent<PmxSecondaryPhysics>();
  }
  IEnumerator Start()
  {
   while((Loader=FindAnyObjectByType<SiCharacterLoader>())==null||!Loader.IsReady||FindAnyObjectByType<IdleMotionPlayer>()==null)
    yield return null;
   yield return null;
   hands=FindAnyObjectByType<ControllerHands>();rig=Loader.Renderer.bones;
   // The old skirt writer must not compete for the same 176 simulated bones.
   Loader.GetComponent<SkirtDynamics>().enabled=false;
   Data=JsonUtility.FromJson<PhysicsData>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"physics/si-physics.json")));
   Build();ResetToAnimation();IsReady=true;
   Debug.Log($"[MGFR PhysX] {Bodies.Length} PMX bodies, {DynamicCount} dynamic, {Joints.Count}/{Data.joints.Length} joints (static-static omitted); chest, sleeves, rear ribbons, skirt, hair and ornaments active; F7 toggle");
  }
  static Vector3 V(float[] a)=>new Vector3(a[0],a[1],a[2]);
  static Quaternion Rotation(float[] a)=>Quaternion.AngleAxis(a[2]*Mathf.Rad2Deg,Vector3.forward)*Quaternion.AngleAxis(a[1]*Mathf.Rad2Deg,Vector3.up)*Quaternion.AngleAxis(a[0]*Mathf.Rad2Deg,Vector3.right);
  static float Damping(float bullet)=>-Mathf.Log(1-Mathf.Clamp(bullet,0,.9999f));
  static bool Pinned(BodyData b)=>b.mode==0||b.name=="tail_jnt1"||b.name.StartsWith("裙子_0_",StringComparison.Ordinal);
  GameObject Object(string name)
  {
   var go=new GameObject(name);go.transform.SetParent(container,false);return go;
  }
  void Build()
  {
   scene=SceneManager.CreateScene("Si isolated PhysX",new CreateSceneParameters(LocalPhysicsMode.Physics3D));world=scene.GetPhysicsScene();
   container=new GameObject("PMX bodies in model metres").transform;SceneManager.MoveGameObjectToScene(container.gameObject,scene);
   int count=Data.bodies.Length;Bodies=new Rigidbody[count];colliders=new Collider[count];offsets=new Vector3[count];restRotations=new Quaternion[count];modelTargets=new Vector3[count];
   localRest=new Vector3[rig.Length];for(int i=0;i<rig.Length;i++)localRest[i]=V(Loader.Data.bones[i].localScaled);
   var dynamicOrder=new List<int>();
   for(int i=0;i<count;i++)
   {
    var d=Data.bodies[i];var go=Object(d.name);go.transform.SetPositionAndRotation(V(d.position)*.08f,Rotation(d.rotation));var rb=go.AddComponent<Rigidbody>();Bodies[i]=rb;
    rb.position=V(d.position)*.08f;rb.rotation=Rotation(d.rotation);restRotations[i]=rb.rotation;
    offsets[i]=rb.position-V(Loader.Data.bones[d.bone].positionScaled);
    rb.isKinematic=Pinned(d);rb.useGravity=false;rb.mass=Mathf.Clamp(Mathf.Sqrt(d.mass),.04f,5);
    rb.linearDamping=Damping(d.linearDamping);rb.angularDamping=Damping(d.angularDamping);
    rb.solverIterations=16;rb.solverVelocityIterations=4;rb.maxAngularVelocity=12;rb.maxDepenetrationVelocity=.5f;
    rb.sleepThreshold=.00002f;
    Vector3 size=V(d.size)*.08f;
    if(d.shape==0){var c=go.AddComponent<SphereCollider>();c.radius=size.x;colliders[i]=c;}
    else if(d.shape==1){var c=go.AddComponent<BoxCollider>();c.size=size*2;colliders[i]=c;}
    else {var c=go.AddComponent<CapsuleCollider>();c.direction=1;c.radius=size.x;c.height=size.y+size.x*2;colliders[i]=c;}
    colliders[i].contactOffset=.001f;
    var material=new PhysicsMaterial(d.name){dynamicFriction=d.friction,staticFriction=d.friction,bounciness=d.restitution};colliders[i].sharedMaterial=material;
    if(!rb.isKinematic){dynamicOrder.Add(i);DynamicCount++;}
   }
   int Depth(int index){int depth=0;for(int p=Data.bodies[index].bone;p>=0;p=Loader.Data.bones[p].parent)depth++;return depth;}
   dynamicOrder.Sort((a,b)=>Depth(a).CompareTo(Depth(b)));order=dynamicOrder.ToArray();
   for(int a=0;a<count;a++)for(int b=a+1;b<count;b++)
    if((Data.bodies[a].mask&(1<<Data.bodies[b].group))==0||(Data.bodies[b].mask&(1<<Data.bodies[a].group))==0)
     Physics.IgnoreCollision(colliders[a],colliders[b],true);
   foreach(var d in Data.joints)
   {
    var a=Bodies[d.a];var b=Bodies[d.b];if(d.a==d.b||(a.isKinematic&&b.isKinematic))continue;
    var j=b.gameObject.AddComponent<ConfigurableJoint>();Joints.Add(j);j.connectedBody=a;j.autoConfigureConnectedAnchor=false;
    Vector3 p=V(d.position)*.08f;Quaternion frame=Rotation(d.rotation);
    j.anchor=Quaternion.Inverse(b.rotation)*(p-b.position);j.connectedAnchor=Quaternion.Inverse(a.rotation)*(p-a.position);
    j.axis=Quaternion.Inverse(b.rotation)*(frame*Vector3.right);j.secondaryAxis=Quaternion.Inverse(b.rotation)*(frame*Vector3.up);
    Vector3 lower=V(d.linearLower)*.08f,upper=V(d.linearUpper)*.08f;
    float Limit(int axis)=>Mathf.Max(Mathf.Abs(lower[axis]),Mathf.Abs(upper[axis]));
    j.xMotion=Limit(0)<.00001f?ConfigurableJointMotion.Locked:ConfigurableJointMotion.Limited;
    j.yMotion=Limit(1)<.00001f?ConfigurableJointMotion.Locked:ConfigurableJointMotion.Limited;
    j.zMotion=Limit(2)<.00001f?ConfigurableJointMotion.Locked:ConfigurableJointMotion.Limited;
    j.linearLimit=new SoftJointLimit{limit=Mathf.Max(Limit(0),Mathf.Max(Limit(1),Limit(2)))};
    Vector3 lo=V(d.angularLower)*Mathf.Rad2Deg,hi=V(d.angularUpper)*Mathf.Rad2Deg;
    float Angular(int axis)=>Mathf.Min(170,Mathf.Max(Mathf.Abs(lo[axis]),Mathf.Abs(hi[axis])));
    j.angularXMotion=Angular(0)<.01f?ConfigurableJointMotion.Locked:ConfigurableJointMotion.Limited;
    j.angularYMotion=Angular(1)<.01f?ConfigurableJointMotion.Locked:ConfigurableJointMotion.Limited;
    j.angularZMotion=Angular(2)<.01f?ConfigurableJointMotion.Locked:ConfigurableJointMotion.Limited;
    j.lowAngularXLimit=new SoftJointLimit{limit=Mathf.Clamp(lo.x,-170,0)};j.highAngularXLimit=new SoftJointLimit{limit=Mathf.Clamp(hi.x,0,170)};
    j.angularYLimit=new SoftJointLimit{limit=Angular(1)};j.angularZLimit=new SoftJointLimit{limit=Angular(2)};
    // PMX is authored for Bullet in MMD units, with artificial mass ratios.
    // Convert torque length-squared and reweight for the compressed PhysX mass.
    float torqueScale=.0064f*b.mass/Mathf.Max(Data.bodies[d.b].mass,.005f);
    JointDrive Drive(float spring)=>new JointDrive{positionSpring=spring*torqueScale,positionDamper=Mathf.Sqrt(Mathf.Max(0,spring*torqueScale))*.025f,maximumForce=100};
    JointDrive LinearDrive(float spring)=>new JointDrive{positionSpring=spring*torqueScale/.0064f,positionDamper=Mathf.Sqrt(Mathf.Max(0,spring*torqueScale/.0064f))*.025f,maximumForce=100};
    j.xDrive=LinearDrive(d.linearSpring[0]);j.yDrive=LinearDrive(d.linearSpring[1]);j.zDrive=LinearDrive(d.linearSpring[2]);
    j.rotationDriveMode=RotationDriveMode.XYAndZ;j.angularXDrive=Drive(d.angularSpring[0]);j.angularYZDrive=Drive((d.angularSpring[1]+d.angularSpring[2])*.5f);
    j.targetRotation=Quaternion.identity;j.enableCollision=false;j.enablePreprocessing=false;
    j.projectionMode=JointProjectionMode.PositionAndRotation;j.projectionDistance=.008f;j.projectionAngle=15;
   }
   var floor=Object("Local ground");floor.transform.position=Vector3.down*.025f;floor.AddComponent<BoxCollider>().size=new Vector3(8,.05f,8);
   for(int h=0;h<2;h++)
   {
    var go=Object("Tracked palm "+h);var rb=go.AddComponent<Rigidbody>();rb.isKinematic=true;rb.useGravity=false;palms[h]=rb;
    palmColliders[h]=go.AddComponent<SphereCollider>();palmColliders[h].radius=.045f;palmColliders[h].enabled=false;
    go.AddComponent<PalmContact>().Owner=this;
   }
  }
  void RestoreAnimatedBones()
  {
   foreach(int i in order){int bone=Data.bodies[i].bone;rig[bone].localPosition=localRest[bone];rig[bone].localRotation=Quaternion.identity;}
  }
  void TargetPose(int i,out Vector3 position,out Quaternion rotation)
  {
   Transform bone=rig[Data.bodies[i].bone];var q=Quaternion.Inverse(Loader.transform.rotation)*bone.rotation;
   position=Loader.transform.InverseTransformPoint(bone.position)+q*offsets[i];rotation=q*restRotations[i];
  }
  public void ResetToAnimation()
  {
   RestoreAnimatedBones();
   for(int i=0;i<Bodies.Length;i++)
   {
    TargetPose(i,out var p,out var q);Bodies[i].position=p;Bodies[i].rotation=q;
    if(!Bodies[i].isKinematic){Bodies[i].linearVelocity=Vector3.zero;Bodies[i].angularVelocity=Vector3.zero;Bodies[i].WakeUp();}
   }
   lastRoot=Loader.transform.position;lastVelocity=Vector3.zero;accumulator=0;
  }
  void LateUpdate()
  {
   if(!IsReady)return;
   if(Input.GetKeyDown(KeyCode.F7)){Simulate=!Simulate;ResetToAnimation();Debug.Log("[MGFR PhysX] active="+Simulate);}
   Tick(Time.deltaTime);
  }
  public void Tick(float delta)
  {
   long started=System.Diagnostics.Stopwatch.GetTimestamp();RestoreAnimatedBones();
   if(!Simulate){LastMilliseconds=0;return;}
   if(Vector3.Distance(Loader.transform.position,lastRoot)>.35f)ResetToAnimation();
   float dt=Mathf.Max(delta,.0001f);var velocity=(Loader.transform.position-lastRoot)/dt;
   Vector3 inertia=Loader.transform.InverseTransformDirection(Vector3.ClampMagnitude(-(velocity-lastVelocity)/dt,35));
   lastRoot=Loader.transform.position;lastVelocity=velocity;
   for(int i=0;i<Bodies.Length;i++)TargetPose(i,out modelTargets[i],out _);
   accumulator+=Mathf.Min(delta,.05f);
   int count=Mathf.FloorToInt(accumulator/Step),step=0;
   while(accumulator>=Step)
   {
    BeforeSubstep?.Invoke(Step,++step/(float)count);
    for(int i=0;i<Bodies.Length;i++)
    {
     var rb=Bodies[i];var d=Data.bodies[i];
     if(rb.isKinematic){TargetPose(i,out var p,out var q);rb.MovePosition(p);rb.MoveRotation(q);}
     else
     {
      if(d.mode==2){rb.position=modelTargets[i];rb.linearVelocity=Vector3.zero;}
      rb.AddForce(Vector3.down*1.8f+inertia,ForceMode.Acceleration);
     }
    }
    for(int h=0;h<2;h++)
    {
     var hand=hands.Hands[h];palmColliders[h].enabled=hand.Active;
     if(hand.Active){palmColliders[h].radius=.045f/Loader.transform.lossyScale.x;palms[h].MovePosition(Loader.transform.InverseTransformPoint(hand.Position));}
    }
    world.Simulate(Step);accumulator-=Step;
   }
   foreach(int i in order)
   {
    var rb=Bodies[i];var d=Data.bodies[i];Quaternion rotation=rb.rotation*Quaternion.Inverse(restRotations[i]);
    var bone=rig[d.bone];bone.rotation=Loader.transform.rotation*rotation;
    if(d.mode==1)bone.position=Loader.transform.TransformPoint(rb.position-rotation*offsets[i]);
   }
   LastMilliseconds=(float)((System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000d/System.Diagnostics.Stopwatch.Frequency);
  }
  public void RecordContact(){Contacts++;}
  void OnDestroy(){if(scene.IsValid()&&scene.isLoaded)SceneManager.UnloadSceneAsync(scene);}
 }
 public sealed class PalmContact:MonoBehaviour
 {
  public PmxSecondaryPhysics Owner;
  void OnCollisionEnter(Collision collision){Owner.RecordContact();}
 }
}
