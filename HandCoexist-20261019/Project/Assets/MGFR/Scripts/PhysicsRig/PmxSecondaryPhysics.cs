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
  Vector3[] offsets,localRest,modelTargets;Quaternion[] restRotations,modelRotations;int[] order;
  Vector3[] previousTargets,stepTargets,lastStepTargets;
  Quaternion[] previousRotations,stepRotations,lastStepRotations;
  int[] anchors;
  bool[] longHair;
  const float HairGravity=6.5f,HairBend=.10f;
  public bool FlexibleLongHair {get;}=Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-rigid-long-hair")<0;
  static bool IsLongHair(BodyData d)=>d.group==4&&(d.name.StartsWith("L_hairE_jnt",StringComparison.Ordinal)||d.name.StartsWith("R_hairE_jnt",StringComparison.Ordinal));
  struct FabricLink {public int a,b;public Vector3 localA,localB;}
  readonly List<FabricLink> fabricLinks=new List<FabricLink>();
  public int SoftLinkCount=>fabricLinks.Count;
  ControllerHands hands;Vector3 lastRoot,lastVelocity;float accumulator;
  public bool PreciseContacts;
  float Step=>PreciseContacts?1f/180f:1f/120f;
  public int LastSubsteps {get;private set;}
  public float DiscardedCatchupSeconds {get;private set;}
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
   Build();ResetToAnimation();
   // Let the thin garment layers settle before accepting hands. This is loading
   // work only; normal rendering never runs a catch-up batch like this.
   for(int warm=0;warm<(FlexibleLongHair?120:8);warm++)Tick(1f/120);
   IsReady=true;
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
   int count=Data.bodies.Length;Bodies=new Rigidbody[count];colliders=new Collider[count];offsets=new Vector3[count];restRotations=new Quaternion[count];modelTargets=new Vector3[count];modelRotations=new Quaternion[count];
   localRest=new Vector3[rig.Length];for(int i=0;i<rig.Length;i++)localRest[i]=V(Loader.Data.bones[i].localScaled);
   longHair=new bool[count];
   var dynamicOrder=new List<int>();
   // PMX masses encode Bullet priority ratios, not garment masses in kilograms.
   // Keep bounded relative weights within each material group and normalize totals.
   float Weight(BodyData body)=>Mathf.Clamp(Mathf.Pow(Mathf.Max(body.mass,.001f),.25f),.5f,2f);
   var groupWeights=new float[16];foreach(var body in Data.bodies)if(!Pinned(body))groupWeights[body.group]+=Weight(body);
   var groupMass=new float[16];groupMass[4]=.2f;groupMass[5]=.3f;groupMass[6]=.07f;groupMass[7]=.04f;
   groupMass[8]=.2f;groupMass[9]=.55f;groupMass[10]=.1f;
   for(int i=0;i<count;i++)
   {
    var d=Data.bodies[i];var go=Object(d.name);go.transform.SetPositionAndRotation(V(d.position)*.08f,Rotation(d.rotation));var rb=go.AddComponent<Rigidbody>();Bodies[i]=rb;
    rb.position=V(d.position)*.08f;rb.rotation=Rotation(d.rotation);restRotations[i]=rb.rotation;
    offsets[i]=rb.position-V(Loader.Data.bones[d.bone].positionScaled);
    longHair[i]=IsLongHair(d);
    rb.isKinematic=Pinned(d);rb.useGravity=false;rb.mass=Mathf.Clamp(Mathf.Sqrt(d.mass),.04f,5);
    if(!rb.isKinematic&&groupMass[d.group]>0)rb.mass=groupMass[d.group]*Weight(d)/groupWeights[d.group];
    rb.linearDamping=Damping(d.linearDamping);rb.angularDamping=Damping(d.angularDamping);
    if(d.group>=4){rb.linearDamping=d.group==4?Mathf.Min(rb.linearDamping,2.5f):3.0f;
     rb.angularDamping=d.group==4?Mathf.Min(rb.angularDamping,3.5f):5.0f;}
    if(FlexibleLongHair&&longHair[i]){rb.linearDamping=1.6f;rb.angularDamping=2.8f;}
    rb.solverIterations=32;rb.solverVelocityIterations=8;rb.maxAngularVelocity=12;rb.maxDepenetrationVelocity=.5f;
    rb.sleepThreshold=.00002f;
    Vector3 size=V(d.size)*.08f;
    // Decorative PMX cloth capsules can be 16 cm thick while neighbouring
    // sleeve nodes are only 3 cm apart. Give fabric a contact thickness rather
    // than treating it as a row of overlapping solid limbs.
    if(d.group>=4)
    {
     if(d.shape==1)size.z=Mathf.Min(size.z,.004f);
     else size.x=Mathf.Min(size.x,d.group==4?.018f:.012f);
     if(d.name.Contains("sleeveD"))size.y=Mathf.Min(size.y,.045f);
    }
    if(d.shape==0){var c=go.AddComponent<SphereCollider>();c.radius=size.x;colliders[i]=c;}
    else if(d.shape==1){var c=go.AddComponent<BoxCollider>();c.size=size*2;colliders[i]=c;}
    else {var c=go.AddComponent<CapsuleCollider>();c.direction=1;c.radius=size.x;c.height=size.y+size.x*2;colliders[i]=c;}
    // Source capsules include end caps beyond the actual arm segment. At a
    // lowered arm these oversized supports sandwich fabric against the torso.
    // Fit total capsule height to the real skeleton, retaining contact coverage.
    if(d.group==0&&d.shape==2&&(d.bone==32||d.bone==58||d.bone==35||d.bone==61||d.bone==38||d.bone==64))
    {
     var capsule=(CapsuleCollider)colliders[i];int end=d.bone==32?35:d.bone==58?61:d.bone==35?38:d.bone==61?64:-1;
     float length=end>=0?Vector3.Distance(V(Loader.Data.bones[d.bone].positionScaled),V(Loader.Data.bones[end].positionScaled)):.07f;
     capsule.radius=Mathf.Min(capsule.radius,d.bone==32||d.bone==58?.032f:.026f);
     capsule.height=Mathf.Max(capsule.radius*2,length*.98f);
    }
    colliders[i].contactOffset=.001f;
    var material=new PhysicsMaterial(d.name){dynamicFriction=d.group>=4?.035f:d.friction,staticFriction=d.group>=4?.05f:d.friction,bounciness=0,frictionCombine=PhysicsMaterialCombine.Minimum};colliders[i].sharedMaterial=material;
    if(!rb.isKinematic){dynamicOrder.Add(i);DynamicCount++;}
   }
   int Depth(int index){int depth=0;for(int p=Data.bodies[index].bone;p>=0;p=Loader.Data.bones[p].parent)depth++;return depth;}
   dynamicOrder.Sort((a,b)=>Depth(a).CompareTo(Depth(b)));order=dynamicOrder.ToArray();
   for(int a=0;a<count;a++)for(int b=a+1;b<count;b++)
    if((Data.bodies[a].mask&(1<<Data.bodies[b].group))==0||(Data.bodies[b].mask&(1<<Data.bodies[a].group))==0)
     Physics.IgnoreCollision(colliders[a],colliders[b],true);
   // PhysX projection cannot resolve the PMX grid's closed constraint loops
   // when several animated anchors move apart. Keep a hard attachment tree;
   // transverse fabric links retain their shape with damped finite forces.
   var sets=new int[count];for(int i=0;i<count;i++)sets[i]=i;
   int Find(int i){while(sets[i]!=i){sets[i]=sets[sets[i]];i=sets[i];}return i;}
   int fixedRoot=-1;for(int i=0;i<count;i++)if(Bodies[i].isKinematic){if(fixedRoot<0)fixedRoot=i;else sets[i]=fixedRoot;}
   foreach(var d in Data.joints)
   {
    var a=Bodies[d.a];var b=Bodies[d.b];if(d.a==d.b||(a.isKinematic&&b.isKinematic))continue;
    Vector3 jointPoint=V(d.position)*.08f;
    if(Find(d.a)==Find(d.b))
    {
     fabricLinks.Add(new FabricLink{a=d.a,b=d.b,localA=Quaternion.Inverse(a.rotation)*(jointPoint-a.position),localB=Quaternion.Inverse(b.rotation)*(jointPoint-b.position)});
     continue;
    }
    sets[Find(d.b)]=Find(d.a);
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
    if(FlexibleLongHair&&longHair[d.a]&&longHair[d.b])
    {
     // The source PMX locks all angular axes on the 16 links in each long
     // strand. Those are rigid bars, not flexible hair. Keep length/attachment,
     // but allow swing around the capsule's actual longitudinal axis.
     j.axis=Vector3.up;j.secondaryAxis=Vector3.right;
     j.angularXMotion=j.angularYMotion=j.angularZMotion=ConfigurableJointMotion.Limited;
     j.lowAngularXLimit=new SoftJointLimit{limit=-12};j.highAngularXLimit=new SoftJointLimit{limit=12};
     float swing=Bodies[d.a].isKinematic?24:30;
     j.angularYLimit=new SoftJointLimit{limit=swing};j.angularZLimit=new SoftJointLimit{limit=swing};
     j.angularXDrive=j.angularYZDrive=default;
     j.rotationDriveMode=RotationDriveMode.Slerp;
     // Support is proportional to the weight and lever arm of the remaining
     // strand, not only the mass of this tiny segment. This retains a gentle
     // authored arc without rigid bars or collapsing the whole strand straight.
     float moment=0,subtreeInertia=0;
     for(int k=d.b;k<count&&longHair[k]&&Data.bodies[k].name[0]==Data.bodies[d.b].name[0];k++)
     {
      var lever=V(Data.bodies[k].position)*.08f-jointPoint;
      moment+=Bodies[k].mass*HairGravity*new Vector2(lever.x,lever.z).magnitude;
      subtreeInertia+=Bodies[k].mass*lever.sqrMagnitude;
     }
     float spring=Mathf.Max(.0002f,moment/HairBend);
     j.slerpDrive=new JointDrive{positionSpring=spring,
       positionDamper=.45f*2*Mathf.Sqrt(spring*Mathf.Max(subtreeInertia,.000001f)),maximumForce=Mathf.Max(.001f,moment*2)};
    }
    j.targetRotation=Quaternion.identity;j.enableCollision=false;j.enablePreprocessing=true;
    j.projectionMode=JointProjectionMode.PositionAndRotation;j.projectionDistance=.0025f;j.projectionAngle=8;
   }
   BuildAnimationFrames();
   Debug.Log($"[MGFR cloth] hard tree={Joints.Count}, damped cross links={fabricLinks.Count}");
   var floor=Object("Local ground");floor.transform.position=Vector3.down*.025f;floor.AddComponent<BoxCollider>().size=new Vector3(8,.05f,8);
   for(int h=0;h<2;h++)
   {
    var go=Object("Tracked palm "+h);var rb=go.AddComponent<Rigidbody>();rb.isKinematic=true;rb.useGravity=false;palms[h]=rb;
    palmColliders[h]=go.AddComponent<SphereCollider>();palmColliders[h].radius=.045f;palmColliders[h].enabled=false;
    go.AddComponent<PalmContact>().Owner=this;
   }
  }
  void BuildAnimationFrames()
  {
   int count=Bodies.Length;anchors=new int[count];Array.Fill(anchors,-1);
   var edges=new List<int>[count];for(int i=0;i<count;i++)edges[i]=new List<int>();
   foreach(var j in Data.joints){edges[j.a].Add(j.b);edges[j.b].Add(j.a);}
   var queue=new Queue<int>();
   for(int i=0;i<count;i++)if(Bodies[i].isKinematic){anchors[i]=i;queue.Enqueue(i);}
   while(queue.Count>0)
   {
    int current=queue.Dequeue();foreach(int next in edges[current])if(anchors[next]<0)
    {anchors[next]=anchors[current];queue.Enqueue(next);}
   }
   previousTargets=new Vector3[count];stepTargets=new Vector3[count];lastStepTargets=new Vector3[count];
   previousRotations=new Quaternion[count];stepRotations=new Quaternion[count];lastStepRotations=new Quaternion[count];
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
  public void RebindSkinRestPose()
  {
   if(!IsReady)return;
   var hairPositions=new Vector3[Bodies.Length];var hairRotations=new Quaternion[Bodies.Length];
   var hairVelocities=new Vector3[Bodies.Length];var hairSpins=new Vector3[Bodies.Length];
   var oldHairAnchors=new Vector3[Bodies.Length];var oldHairTurns=new Quaternion[Bodies.Length];
   var keepHair=new bool[Bodies.Length];
   for(int i=0;i<Bodies.Length;i++)if(FlexibleLongHair&&longHair[i]&&!Bodies[i].isKinematic)
   {
    int bone=Data.bodies[i].bone;
    keepHair[i]=(localRest[bone]-V(Loader.Data.bones[bone].localScaled)).sqrMagnitude<.000004f;
    hairPositions[i]=Bodies[i].position;hairRotations[i]=Bodies[i].rotation;
    hairVelocities[i]=Bodies[i].linearVelocity;hairSpins[i]=Bodies[i].angularVelocity;
    int a=anchors[i];oldHairAnchors[i]=Bodies[a].position;oldHairTurns[i]=Bodies[a].rotation;
   }
   for(int i=0;i<rig.Length;i++)localRest[i]=V(Loader.Data.bones[i].localScaled);
   // Keep proxy collisions only where the selected skin has weighted geometry.
   // A bikini must not leave invisible old skirt/sleeve grab targets in the room.
   var used=new bool[rig.Length];
   var pinned=new bool[rig.Length];
   for(int i=0;i<Bodies.Length;i++)if(Bodies[i].isKinematic)pinned[Data.bodies[i].bone]=true;
   void Mark(int bone,float weight)
   {
    if(weight<.01f)return;
    for(int p=bone;p>=0;p=Loader.Data.bones[p].parent){used[p]=true;if(pinned[p])break;}
   }
   foreach(var w in Loader.Renderer.sharedMesh.boneWeights)
   {Mark(w.boneIndex0,w.weight0);Mark(w.boneIndex1,w.weight1);Mark(w.boneIndex2,w.weight2);Mark(w.boneIndex3,w.weight3);}
   for(int i=0;i<Bodies.Length;i++)colliders[i].enabled=Data.bodies[i].group<4||used[Data.bodies[i].bone];
   ResetToAnimation();
   for(int i=0;i<Bodies.Length;i++)if(keepHair[i])
   {
    // Barefoot skin lowers the rest skeleton by about 6.3 cm. Carry the
    // settled chain through its own attachment frame, rather than leaving its
    // dynamic points behind while the fixed hair root jumps to the new height.
    int a=anchors[i];var turn=Bodies[a].rotation*Quaternion.Inverse(oldHairTurns[i]);
    Bodies[i].position=Bodies[a].position+turn*(hairPositions[i]-oldHairAnchors[i]);
    Bodies[i].rotation=turn*hairRotations[i];
    Bodies[i].linearVelocity=turn*hairVelocities[i];Bodies[i].angularVelocity=turn*hairSpins[i];Bodies[i].WakeUp();
   }
  }
  public void ResetToAnimation()
  {
   RestoreAnimatedBones();
   for(int i=0;i<Bodies.Length;i++)
   {
    TargetPose(i,out var p,out var q);Bodies[i].position=p;Bodies[i].rotation=q;
    previousTargets[i]=p;previousRotations[i]=q;
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
   // Cache animated targets once, not 506 transform queries per substep.
   for(int i=0;i<Bodies.Length;i++)TargetPose(i,out modelTargets[i],out modelRotations[i]);
   float fixedStep=Step;accumulator+=Mathf.Max(0,delta);
   int requested=Mathf.FloorToInt(accumulator/fixedStep);
   int count=Mathf.Min(requested,3);LastSubsteps=count;
   // A missed display frame must not create a physics catch-up spiral.
   // Discard wall time, keeping small fixed steps and the world anchor intact.
   DiscardedCatchupSeconds+=Mathf.Max(0,requested-count)*fixedStep;
   accumulator-=requested*fixedStep;
   for(int step=0;step<count;step++)
   {
    float progress=(step+1)/(float)count;
    for(int i=0;i<Bodies.Length;i++)
    {
     lastStepTargets[i]=step==0?previousTargets[i]:stepTargets[i];
     lastStepRotations[i]=step==0?previousRotations[i]:stepRotations[i];
     stepTargets[i]=Vector3.Lerp(previousTargets[i],modelTargets[i],progress);
     stepRotations[i]=Quaternion.Slerp(previousRotations[i],modelRotations[i],progress);
    }
    // Carry most of the animated attachment frame into cloth/hair before
    // simulating the remaining inertia. The joints no longer drag a stationary
    // sheet through a moving arm in one step; hand forces remain dynamic.
    foreach(int i in order)
    {
     int a=anchors[i];if(a<0||Data.bodies[i].group<4)continue;
     var rb=Bodies[i];int group=Data.bodies[i].group;
     float follow=group==5?1f:group==4?.90f:.95f;
     var turn=stepRotations[a]*Quaternion.Inverse(lastStepRotations[a]);
     var carried=stepTargets[a]+turn*(rb.position-lastStepTargets[a]);
     rb.position=Vector3.Lerp(rb.position,carried,follow);
     var carriedTurn=Quaternion.Slerp(Quaternion.identity,turn,follow);
     rb.rotation=carriedTurn*rb.rotation;rb.linearVelocity=carriedTurn*rb.linearVelocity;rb.angularVelocity=carriedTurn*rb.angularVelocity;
    }
    BeforeSubstep?.Invoke(fixedStep,progress);
    foreach(var link in fabricLinks)
    {
     var a=Bodies[link.a];var b=Bodies[link.b];var pa=a.position+a.rotation*link.localA;var pb=b.position+b.rotation*link.localB;
     float mass=a.isKinematic?b.mass:b.isKinematic?a.mass:a.mass*b.mass/(a.mass+b.mass);
     const float frequency=2*Mathf.PI*5;
     // Backward PD avoids injecting energy when a sleeve is squeezed between
     // animated support and skirt. Bound force without resetting cloth positions.
     float denominator=1+2*frequency*fixedStep+frequency*frequency*fixedStep*fixedStep;
     var force=mass*Vector3.ClampMagnitude((frequency*frequency*(pb-pa)+
       (2*frequency+frequency*frequency*fixedStep)*(b.GetPointVelocity(pb)-a.GetPointVelocity(pa)))/denominator,12);
     if(!a.isKinematic)a.AddForceAtPosition(force,pa);if(!b.isKinematic)b.AddForceAtPosition(-force,pb);
    }
    for(int i=0;i<Bodies.Length;i++)
    {
     var rb=Bodies[i];var d=Data.bodies[i];
     if(rb.isKinematic){rb.MovePosition(stepTargets[i]);rb.MoveRotation(stepRotations[i]);}
     else
     {
      if(d.mode==2){rb.position=stepTargets[i];rb.linearVelocity=Vector3.zero;}
      rb.AddForce(Vector3.down*(FlexibleLongHair&&longHair[i]?HairGravity:1.8f)+inertia,ForceMode.Acceleration);
     }
    }
    for(int h=0;h<2;h++)
    {
     var hand=hands.Hands[h];palmColliders[h].enabled=hand.Active;
     if(hand.Active){palmColliders[h].radius=.045f/Loader.transform.lossyScale.x;palms[h].MovePosition(Loader.transform.InverseTransformPoint(hand.Position));}
    }
    world.Simulate(fixedStep);
    foreach(int i in order)
    {
     var rb=Bodies[i];rb.linearVelocity=Vector3.ClampMagnitude(rb.linearVelocity,2.5f);
     rb.angularVelocity=Vector3.ClampMagnitude(rb.angularVelocity,10);
    }
   }
   if(count>0)for(int i=0;i<Bodies.Length;i++){previousTargets[i]=modelTargets[i];previousRotations[i]=modelRotations[i];}
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
