using System;
using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Experience;
using MGFR.Attention;
using MGFR.Rendering;

namespace MGFR.PhysicsRig
{
 public sealed class PmxPhysicsReview:MonoBehaviour
 {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-physics-review")>=0)
    new GameObject("PMX physics review").AddComponent<PmxPhysicsReview>();
  }
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string dir=args[Array.IndexOf(args,"-mgfr-physics-dir")+1];Directory.CreateDirectory(dir);
   PmxSecondaryPhysics physics;
   while((physics=FindAnyObjectByType<PmxSecondaryPhysics>())==null||!physics.IsReady)yield return null;
   while(!FindAnyObjectByType<SiEndfieldClothing>().IsReady)yield return null;
   physics.enabled=false;var loader=physics.Loader;
   var idle=loader.GetComponent<IdleMotionPlayer>();idle.enabled=false;
   loader.GetComponent<FaceAttentionController>().AutoUpdate=false;
   var hands=FindAnyObjectByType<ControllerHands>();hands.TestInput=true;
   loader.gameObject.layer=8;
   var camera=new GameObject("Physics comparison camera").AddComponent<Camera>();camera.CopyFrom(Camera.main);
   camera.enabled=false;camera.cullingMask=1<<8;camera.stereoTargetEye=StereoTargetEyeMask.None;
   var rt=new RenderTexture(900,1100,24);rt.antiAliasing=4;camera.targetTexture=rt;
   var image=new Texture2D(900,1100,TextureFormat.RGB24,false);
   Vector3 original=loader.transform.position;float chestPeak=0,rearPeak=0,peakMs=0,totalMs=0,maxGap=0,maxViolation=0;string worst="";bool finite=true;
   physics.ResetToAnimation();
   const int frames=240;
   for(int f=0;f<frames;f++)
   {
    float t=f/60f;idle.Apply(t);
    // A short lateral movement and upper-body turn exercise real inertia.
    loader.transform.position=original+Vector3.right*(f<60?0:.04f*Mathf.Sin((t-1)*Mathf.PI*2));
    loader.Renderer.bones[13].localRotation*=Quaternion.Euler(0,Mathf.Sin(t*3)*8,Mathf.Sin(t*4)*3);
    // The proxy touches the left sleeve late in the sequence.
    hands.SetSimulatedHand(0,loader.transform.TransformPoint(new Vector3(.31f,1.1f,-.02f)),false,f>150);
    physics.Tick(1f/60f);peakMs=Mathf.Max(peakMs,physics.LastMilliseconds);totalMs+=physics.LastMilliseconds;
    if(f==30||f==90||f==150||f==210)
    {
     int frame=f;camera.transform.position=loader.transform.TransformPoint(new Vector3(f<150?.65f:-.65f,1.05f,f<150?-2.45f:2.45f));
     camera.transform.LookAt(loader.transform.TransformPoint(new Vector3(0,.95f,0)));camera.fieldOfView=43;
     camera.Render();RenderTexture.active=rt;image.ReadPixels(new Rect(0,0,900,1100),0,0);image.Apply();RenderTexture.active=null;
     File.WriteAllBytes(Path.Combine(dir,$"physics-{frame:D3}.png"),image.EncodeToPNG());
    }
    foreach(int i in new[]{278,281})
    {
     var bone=loader.Renderer.bones[physics.Data.bodies[i].bone];chestPeak=Mathf.Max(chestPeak,Quaternion.Angle(Quaternion.identity,bone.localRotation));
    }
    foreach(int i in new[]{220,248,270,472,487})
    {
     var bone=loader.Renderer.bones[physics.Data.bodies[i].bone];rearPeak=Mathf.Max(rearPeak,Quaternion.Angle(Quaternion.identity,bone.localRotation));
    }
    foreach(var body in physics.Bodies)
    {
     var p=body.position;finite&=!float.IsNaN(p.x)&&!float.IsInfinity(p.x)&&p.sqrMagnitude<25;
    }
    if(f>30)foreach(var j in physics.Joints)
    {
     Vector3 delta=j.transform.TransformPoint(j.anchor)-j.connectedBody.transform.TransformPoint(j.connectedAnchor);
     maxGap=Mathf.Max(maxGap,delta.magnitude);
     Vector3 x=j.transform.TransformDirection(j.axis).normalized,y=j.transform.TransformDirection(j.secondaryAxis).normalized,z=Vector3.Cross(x,y).normalized;
     float Error(ConfigurableJointMotion motion,float amount)=>motion==ConfigurableJointMotion.Free?0:Mathf.Max(0,Mathf.Abs(amount)-(motion==ConfigurableJointMotion.Locked?0:j.linearLimit.limit));
     float violation=Mathf.Max(Error(j.xMotion,Vector3.Dot(delta,x)),Mathf.Max(Error(j.yMotion,Vector3.Dot(delta,y)),Error(j.zMotion,Vector3.Dot(delta,z))));
     if(violation>maxViolation){maxViolation=violation;worst=j.gameObject.name;}

    }
    if(f%8==0)yield return null;
   }
   bool pass=finite&&chestPeak>.01f&&rearPeak>.01f&&maxViolation<.035f;
   string report=$"pass={pass}\nbodies={physics.Bodies.Length}\ndynamic={physics.DynamicCount}\njoints={physics.Joints.Count}\nchestPeakDegrees={chestPeak}\nrearPeakDegrees={rearPeak}\nmaxJointAnchorGapMetres={maxGap}\nmaxTranslationConstraintViolationMetres={maxViolation}\nworstConstraintBody={worst}\npeakPhysicsCpuMs={peakMs}\nmeanPhysicsCpuMs={totalMs/frames}\nhandContacts={physics.Contacts}\nfiniteBounds={finite}\nframes={frames}\n";
   File.WriteAllText(Path.Combine(dir,"physics-report.txt"),report);Debug.Log("[MGFR PhysX review] "+report.Replace('\n',' '));
   camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(image);Application.Quit(pass?0:1);
  }
 }
}
