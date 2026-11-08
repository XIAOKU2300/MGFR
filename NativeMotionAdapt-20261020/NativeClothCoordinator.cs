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
  readonly Matrix4x4[] previous=new Matrix4x4[4];bool previousReady,active;string skin;
  List<SwimsuitClothSolver.Capsule> body;List<SwimsuitClothSolver.Capsule>[] handContacts;
  MethodInfo updateDrivers,updateGrabs,buildContacts;float maximumMs;int frames;
  public float LastMilliseconds {get;private set;}public int AddedCapsules {get;private set;}public bool IsReady=>visual!=null;
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
   var positions=new Vector3[solver.Particles.Length];var oldPositions=new Vector3[positions.Length];
   if(previousReady)for(int i=0;i<positions.Length;i++){var p=solver.Particles[i];var carry=drivers[p.group]*previous[p.group].inverse;positions[i]=carry.MultiplyPoint3x4(p.position);oldPositions[i]=carry.MultiplyPoint3x4(p.previous);}
   solver.SetTargets(drivers);
   if(previousReady)for(int i=0;i<positions.Length;i++){var p=solver.Particles[i];p.position=positions[i];p.previous=oldPositions[i];solver.Particles[i]=p;}
   for(int i=0;i<4;i++)previous[i]=drivers[i];previousReady=true;
   updateGrabs.Invoke(cloth,new object[]{delta});buildContacts.Invoke(cloth,null);int original=body.Count;AddAnimatedContacts();AddedCapsules=body.Count-original;
   if(hands.Physics.Simulate)solver.Step(delta,body,handContacts,skins.Loader.transform.TransformDirection(new Vector3(.08f,0,.025f)));else solver.Reset();
   solver.WriteVertices(drivers,skins.Loader.transform.worldToLocalMatrix,vertices);visual.vertices=vertices;visual.RecalculateNormals();visual.RecalculateTangents();visual.RecalculateBounds();
   if(renderer.sharedMaterial!=skins.Loader.Materials[10])renderer.sharedMaterial=skins.Loader.Materials[10];
   LastMilliseconds=(System.Diagnostics.Stopwatch.GetTimestamp()-start)*1000f/System.Diagnostics.Stopwatch.Frequency;maximumMs=Mathf.Max(maximumMs,LastMilliseconds);frames++;
   if(frames%300==0)Debug.Log("NATIVE_CLOTH_CONTACTS added="+AddedCapsules+" offset="+solver.MaximumOffset+" ms="+LastMilliseconds+" maxMs="+maximumMs);
  }
  void Add(Vector3 a,Vector3 b,float r){body.Add(new SwimsuitClothSolver.Capsule{a=a,b=b,radius=r*Mathf.Abs(skins.Loader.transform.lossyScale.x)});}
  void AddAnimatedContacts(){
   var root=skins.Loader.transform;
   // Several narrow capsules fit the torso width without inflating arms or changing animation.
   var chest=(bones[13].position+bones[15].position)*.5f;var side=root.right*.055f;
   Add(bones[13].position+side,bones[15].position+side,.066f);Add(bones[13].position-side,bones[15].position-side,.066f);
   var pelvis=(bones[21].position+bones[25].position)*.5f;Add(pelvis-side,pelvis+side,.071f);
   for(int h=0;h<2;h++){
    int wrist=h==0?38:64;int[] first=h==0?new[]{40,43,46,49,52}:new[]{66,69,72,75,78};
    var palm=(bones[first[1]].position+bones[first[4]].position)*.5f;Add(bones[wrist].position,palm,.025f);
    for(int f=0;f<5;f++){int a=first[f];Add(bones[a].position,bones[a+1].position,f==0?.010f:.008f);Add(bones[a+1].position,bones[a+2].position,.007f);}
   }
  }
  void OnDestroy(){if(cloth!=null)cloth.Manual=false;}
 }
}
