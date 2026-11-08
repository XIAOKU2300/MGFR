using System;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.Hands;

namespace MGFR.BareHands
{
 public sealed class HandDepthMesh
 {
  public static readonly int[,] Segments={{2,3},{3,4},{4,5},{6,7},{7,8},{8,9},{9,10},
   {11,12},{12,13},{13,14},{14,15},{16,17},{17,18},{18,19},{19,20},{21,22},{22,23},{23,24},{24,25}};
  public readonly GameObject Object;
  public readonly Mesh Mesh;
  public readonly Transform[] Bones=new Transform[26];
  public readonly SkinnedMeshRenderer Renderer;
  readonly Transform[] hierarchy;
  readonly float referenceWidth,referenceLength;
  public bool FitSkin=true;public float SkinScale {get;private set;}=1;
  double lastFit;int lastLayer=-1;
  readonly HandOcclusionEnvelope envelope;
  public bool AnatomicalOcclusion=true;
  public void DisposeEnvelope()=>envelope.Dispose();

  public HandDepthMesh(int hand,Material material)
  {
   Object=UnityEngine.Object.Instantiate(Resources.Load<GameObject>("BareHands/"+(hand==0?"LeftHand":"RightHand")));
   Object.name="Skinned hand depth "+hand;
   hierarchy=Object.GetComponentsInChildren<Transform>(true);
   for(int i=0;i<26;i++)
   {
    string name=(i==0?XRHandJointID.Palm:i==1?XRHandJointID.Wrist:XRHandJointIDUtility.FromIndex(i)).ToString();
    foreach(var bone in hierarchy)
     if(bone.name.EndsWith(name,StringComparison.OrdinalIgnoreCase)){Bones[i]=bone;break;}
    if(Bones[i]==null)throw new InvalidOperationException("Official hand mesh missing "+name);
   }
   referenceWidth=Vector3.Distance(Bones[7].position,Bones[22].position);
   referenceLength=Vector3.Distance(Bones[1].position,Bones[12].position);
   Renderer=Object.GetComponentInChildren<SkinnedMeshRenderer>();
   Mesh=UnityEngine.Object.Instantiate(Renderer.sharedMesh);Renderer.sharedMesh=Mesh;
   Renderer.sharedMaterial=material;Renderer.shadowCastingMode=ShadowCastingMode.Off;Renderer.receiveShadows=false;
   Renderer.updateWhenOffscreen=true;
   Debug.Log($"[MGFR hand mesh] hand={hand} joints=26 vertices={Mesh.vertexCount} source=UnityXRHands renderPose=latestSDK physicsPose=stabilized metricEnvelope=True automaticJointRadii=True globalEnlargement=False");
   Object.SetActive(false);
   envelope=new HandOcclusionEnvelope(material);
  }
  public static void PalmShape(HandFrame f,out Vector3 center,out Quaternion rotation,out Vector3 size)
  {
   var knuckles=(f.Joints[7].position+f.Joints[12].position+f.Joints[17].position+f.Joints[22].position)*.25f;
   var wrist=f.Joints[1].position;var along=(knuckles-wrist).normalized;
   var across=(f.Joints[7].position-f.Joints[22].position).normalized;
   var normal=Vector3.Cross(across,along).normalized;
   rotation=Quaternion.LookRotation(normal,along);center=(wrist+knuckles)*.5f;
   size=new Vector3(Vector3.Distance(f.Joints[7].position,f.Joints[22].position)+.013f*f.Scale,Vector3.Distance(wrist,knuckles)+.012f*f.Scale,.022f*f.Scale);
  }
  public void Update(HandFrame f,bool show)
  {
   bool active=show&&f.Tracked;if(Object.activeSelf!=active)Object.SetActive(active);
   envelope.Update(f,active&&AnatomicalOcclusion,Object.layer,Time.realtimeSinceStartupAsDouble);
   Renderer.enabled=!AnatomicalOcclusion;
   if(!active||AnatomicalOcclusion)return;
   if(FitSkin)
   {
    float width=Vector3.Distance(f.Joints[7].position,f.Joints[22].position)/referenceWidth;
    float length=Vector3.Distance(f.Joints[1].position,f.Joints[12].position)/referenceLength;
    float target=Mathf.Clamp((width+length)*.5f,.85f,1.45f);
    double now=Time.realtimeSinceStartupAsDouble;float dt=lastFit==0?.016f:(float)(now-lastFit);lastFit=now;
    SkinScale=Mathf.Lerp(SkinScale,target,1-Mathf.Exp(-4*dt));Object.transform.localScale=Vector3.one*SkinScale;
   }
   // Parent-first order prevents a wrist move from moving the already-updated palm.
   if(f.Valid[1])Bones[1].SetPositionAndRotation(f.Joints[1].position,f.Joints[1].rotation);
   if(f.Valid[0])Bones[0].SetPositionAndRotation(f.Joints[0].position,f.Joints[0].rotation);
   for(int i=2;i<26;i++)if(f.Valid[i])Bones[i].SetPositionAndRotation(f.Joints[i].position,f.Joints[i].rotation);
   if(lastLayer!=Object.layer){lastLayer=Object.layer;foreach(var child in hierarchy)child.gameObject.layer=lastLayer;}
  }
 }
}
