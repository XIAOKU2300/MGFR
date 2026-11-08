using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using MGFR.Skins;
using MGFR.Skins.ClothPhysics;
using MGFR.BareHands;
namespace MGFR.StructuredVoiceFinal {
 // The existing cloth still owns garment selection and grabs. This coordinator
 // supplies current animation frames and body/character-hand contacts to its solver.
 [DefaultExecutionOrder(1400)]public sealed class NativeClothCoordinator:MonoBehaviour {
  SwimsuitClothRuntime cloth;SiSkinSwitcher skins;BareHandInteraction hands;Mesh visual;MeshRenderer renderer;Vector3[] vertices;Matrix4x4[] drivers;Transform[] bones;
  Vector3[] carryPosition,carryPrevious;readonly Matrix4x4[] carry=new Matrix4x4[4];
  readonly Matrix4x4[] previous=new Matrix4x4[4];bool previousReady,active;string skin;
  readonly List<SwimsuitClothSolver.Capsule> stepBody=new List<SwimsuitClothSolver.Capsule>();
  List<SwimsuitClothSolver.Capsule> body;List<SwimsuitClothSolver.Capsule>[] handContacts;
  MethodInfo updateDrivers,updateGrabs,buildContacts;float maximumMs;int frames;
  public float LastMilliseconds {get;private set;}public int AddedCapsules {get;private set;}public float ResidualPenetration {get;private set;}public bool IsReady=>visual!=null;
  static readonly BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
  object Field(string name)=>typeof(SwimsuitClothRuntime).GetField(name,Flags).GetValue(cloth);
  void Bind(){cloth=FindAnyObjectByType<SwimsuitClothRuntime>();skins=FindAnyObjectByType<SiSkinSwitcher>();hands=FindAnyObjectByType<BareHandInteraction>();if(cloth==null||skins==null||!skins.IsReady||hands==null||!hands.IsReady)return;
   cloth.Manual=true;updateDrivers=typeof(SwimsuitClothRuntime).GetMethod("UpdateDrivers",Flags);updateGrabs=typeof(SwimsuitClothRuntime).GetMethod("UpdateGrabs",Flags);buildContacts=typeof(SwimsuitClothRuntime).GetMethod("BuildContacts",Flags);
  }
  void LateUpdate(){
   if(cloth==null||updateDrivers==null){Bind();if(cloth==null||updateDrivers==null)return;}
   if(!cloth.Active){if(active)cloth.Tick(0);active=false;previousReady=false;skin=skins.CurrentId;return;}
   long start=System.Diagnostics.Stopwatch.GetTimestamp();float delta=Mathf.Clamp(Time.unscaledDeltaTime,.001f,.0333f);
   if(!active||cloth.Solver==null||skin!=skins.CurrentId){cloth.Tick(0);active=true;skin=skins.CurrentId;previousReady=false;
    visual=(Mesh)Field("visual");renderer=(MeshRenderer)Field("clothRenderer");vertices=(Vector3[])Field("vertices");drivers=(Matrix4x4[])Field("drivers");bones=(Transform[])Field("cachedBones");body=(List<SwimsuitClothSolver.Capsule>)Field("body");handContacts=(List<SwimsuitClothSolver.Capsule>[])Field("handCapsules");
   }
   if(visual==null)return;
   updateDrivers.Invoke(cloth,null);var solver=cloth.Solver;
   // Carry simulated positions and velocities through the complete animated frame
   // transform. The solver then adds cloth inertia, gravity and contact response.
   if(carryPosition==null||carryPosition.Length!=solver.Particles.Length){carryPosition=new Vector3[solver.Particles.Length];carryPrevious=new Vector3[solver.Particles.Length];}
   var positions=carryPosition;var oldPositions=carryPrevious;
   if(previousReady)for(int g=0;g<4;g++)carry[g]=drivers[g]*previous[g].inverse;
   if(previousReady)for(int i=0;i<positions.Length;i++){var p=solver.Particles[i];positions[i]=carry[p.group].MultiplyPoint3x4(p.position);oldPositions[i]=carry[p.group].MultiplyPoint3x4(p.previous);}
   solver.SetTargets(drivers);
   if(previousReady)for(int i=0;i<positions.Length;i++){var p=solver.Particles[i];p.position=positions[i];p.previous=oldPositions[i];solver.Particles[i]=p;}
   for(int i=0;i<4;i++)previous[i]=drivers[i];previousReady=true;
   updateGrabs.Invoke(cloth,new object[]{delta});buildContacts.Invoke(cloth,null);int original=body.Count;stepBody.Clear();stepBody.AddRange(body);AddAnimatedContacts();AddedCapsules=body.Count-original;
   float currentScale=Mathf.Abs(skins.Loader.transform.lossyScale.x);
   float referenceScale=(float)SolverScaleField.GetValue(solver);float factor=referenceScale/Mathf.Max(.001f,currentScale);
   var wind=skins.Loader.transform.TransformDirection(new Vector3(.08f,0,.025f));
   if(hands.Physics.Simulate&&Mathf.Abs(factor-1)>.00001f&&Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-scale-old-metric")<0){
    // The solver's rest lengths and travel are fixed at its creation scale.
    // Simulate in that metric, then restore real world state before every other
    // system reads particles, grips, targets or the visible cloth surface.
    var origin=skins.Loader.transform.position;var normalize=Matrix4x4.TRS(origin,Quaternion.identity,Vector3.one*factor)*Matrix4x4.Translate(-origin);
    ReframeSolver(solver,normalize);ScaleContacts(stepBody,scaledStepBody,normalize,factor);ScaleContacts(body,scaledFullBody,normalize,factor);
    for(int h=0;h<2;h++)ScaleContacts(handContacts[h],scaledHands[h],normalize,factor);
    var realBody=body;body=scaledFullBody;
    try{solver.Step(delta,scaledStepBody,scaledHands,wind);FinishBodyContacts(solver);if(frames%30==0)ResidualPenetration/=factor;}
    finally{body=realBody;ReframeSolver(solver,normalize.inverse);}
   }else{if(hands.Physics.Simulate)solver.Step(delta,stepBody,handContacts,wind);else solver.Reset();FinishBodyContacts(solver);}
   solver.WriteVertices(drivers,skins.Loader.transform.worldToLocalMatrix,vertices);visual.vertices=vertices;visual.RecalculateNormals();if(frames%3==0)visual.RecalculateTangents();visual.RecalculateBounds();
   if(renderer.sharedMaterial!=skins.Loader.Materials[10])renderer.sharedMaterial=skins.Loader.Materials[10];
   LastMilliseconds=(System.Diagnostics.Stopwatch.GetTimestamp()-start)*1000f/System.Diagnostics.Stopwatch.Frequency;maximumMs=Mathf.Max(maximumMs,LastMilliseconds);frames++;
   if(frames%300==0)Debug.Log("NATIVE_CLOTH_CONTACTS added="+AddedCapsules+" offset="+solver.MaximumOffset+" ms="+LastMilliseconds+" maxMs="+maximumMs);
  }
  struct ContactShape {public Vector3 a,axis,min,max;public float radius,invLength;}
  readonly ContactShape[] shapes=new ContactShape[80];
  void FinishBodyContacts(SwimsuitClothSolver solver){
   int count=Mathf.Min(body.Count,shapes.Length);
   for(int i=0;i<count;i++){var c=body[i];var axis=c.b-c.a;var margin=Vector3.one*c.radius;shapes[i]=new ContactShape{a=c.a,axis=axis,min=Vector3.Min(c.a,c.b)-margin,max=Vector3.Max(c.a,c.b)+margin,radius=c.radius,invLength=axis.sqrMagnitude>1e-10f?1/axis.sqrMagnitude:0};}
   for(int iteration=0;iteration<8;iteration++)for(int i=0;i<solver.Particles.Length;i++){
    var p=solver.Particles[i];if(p.inverseMass==0||!solver.EnabledGroups[p.group])continue;
    for(int c=0;c<count;c++){var shape=shapes[c];var v=p.position;if(v.x<shape.min.x||v.x>shape.max.x||v.y<shape.min.y||v.y>shape.max.y||v.z<shape.min.z||v.z>shape.max.z)continue;
     float t=Mathf.Clamp01(Vector3.Dot(v-shape.a,shape.axis)*shape.invLength);var normal=v-(shape.a+shape.axis*t);float squared=normal.sqrMagnitude;
     if(squared>=shape.radius*shape.radius||squared<1e-12f)continue;var correction=normal*(shape.radius/Mathf.Sqrt(squared)-1);p.position+=correction;p.previous+=correction;
    }solver.Particles[i]=p;
   }
   // A bounded diagnostic sample; do not add a full collision sweep to every display frame.
   if(frames%30!=0)return;ResidualPenetration=0;
   for(int i=0;i<solver.Particles.Length;i++){var p=solver.Particles[i];if(p.inverseMass==0||!solver.EnabledGroups[p.group])continue;
    for(int c=0;c<count;c++){var shape=shapes[c];var v=p.position;if(v.x<shape.min.x||v.x>shape.max.x||v.y<shape.min.y||v.y>shape.max.y||v.z<shape.min.z||v.z>shape.max.z)continue;
     float t=Mathf.Clamp01(Vector3.Dot(v-shape.a,shape.axis)*shape.invLength);float depth=shape.radius-Vector3.Distance(v,shape.a+shape.axis*t);ResidualPenetration=Mathf.Max(ResidualPenetration,depth);}
   }
  }
  void Add(Vector3 a,Vector3 b,float r){body.Add(new SwimsuitClothSolver.Capsule{a=a,b=b,radius=r*Mathf.Abs(skins.Loader.transform.lossyScale.x)});}
  void AddAnimatedContacts(){
   var root=skins.Loader.transform;
   // Several narrow capsules fit the torso width without inflating arms or changing animation.
   var chest=(bones[13].position+bones[15].position)*.5f;var side=root.TransformVector(Vector3.right*.055f);
   // Keep the established fitted chest capsule. Inflating its shoulder width
   // pushes this costume's neckline above its attachment line.
   var pelvis=(bones[21].position+bones[25].position)*.5f;Add(pelvis-side,pelvis+side,.071f);
   for(int h=0;h<2;h++){
    int wrist=h==0?38:64;int[] first=h==0?new[]{40,43,46,49,52}:new[]{66,69,72,75,78};
    var palm=(bones[first[1]].position+bones[first[4]].position)*.5f;Add(bones[wrist].position,palm,.025f);
    for(int f=0;f<5;f++){int a=first[f];Add(bones[a].position,bones[a+1].position,f==0?.010f:.008f);Add(bones[a+1].position,bones[a+2].position,.007f);}
   }
  }
  static readonly FieldInfo SolverScaleField=typeof(SwimsuitClothSolver).GetField("scale",BindingFlags.Instance|BindingFlags.NonPublic);
  readonly List<SwimsuitClothSolver.Capsule> scaledStepBody=new List<SwimsuitClothSolver.Capsule>(),scaledFullBody=new List<SwimsuitClothSolver.Capsule>();
  readonly List<SwimsuitClothSolver.Capsule>[] scaledHands={new List<SwimsuitClothSolver.Capsule>(),new List<SwimsuitClothSolver.Capsule>()};
  static void ReframeSolver(SwimsuitClothSolver solver,Matrix4x4 transform){
   for(int i=0;i<solver.Particles.Length;i++){var p=solver.Particles[i];p.position=transform.MultiplyPoint3x4(p.position);p.previous=transform.MultiplyPoint3x4(p.previous);p.target=transform.MultiplyPoint3x4(p.target);solver.Particles[i]=p;}
   for(int h=0;h<2;h++){var grip=solver.Grips[h];if(grip.particle<0)continue;grip.target=transform.MultiplyPoint3x4(grip.target);grip.offset=transform.MultiplyVector(grip.offset);solver.Grips[h]=grip;}
  }
  static void ScaleContacts(List<SwimsuitClothSolver.Capsule> input,List<SwimsuitClothSolver.Capsule> output,Matrix4x4 transform,float factor){output.Clear();foreach(var c in input)output.Add(new SwimsuitClothSolver.Capsule{a=transform.MultiplyPoint3x4(c.a),b=transform.MultiplyPoint3x4(c.b),radius=c.radius*factor});}
  void OnDestroy(){if(cloth!=null)cloth.Manual=false;}
 }
}
