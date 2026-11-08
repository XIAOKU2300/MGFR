using System;
using UnityEngine;
using UnityEngine.XR.Hands;

namespace MGFR.BareHands
{
 public static class ContinuousHandsBuild
 {
  public static void Build()
  {
   var go=new GameObject("Hand update phase check");var source=go.AddComponent<HandJointSource>();
   var raw=new HandFrame{Tracked=true,ValidCount=26,Timestamp=1};
   for(int i=0;i<26;i++){raw.Valid[i]=true;raw.Radius[i]=.008f;raw.Joints[i]=new Pose(new Vector3(i*.004f,1,.5f),Quaternion.identity);}
   source.AcceptSample(0,raw,XRHandSubsystem.UpdateType.Dynamic,1);
   var physics=source.Frames[0].Joints[10];int count=source.PhysicsSamples;
   for(int i=0;i<26;i++)raw.Joints[i].position+=Vector3.right*.05f;
   source.AcceptSample(0,raw,XRHandSubsystem.UpdateType.BeforeRender,1.005);
   if(source.PhysicsSamples!=count||source.Frames[0].Joints[10].position!=physics.position)throw new Exception("BeforeRender changed physics input");
   if(source.RenderFrames[0].Joints[10].position!=raw.Joints[10].position)throw new Exception("Render pose must match SDK exactly without extrapolation");
   UnityEngine.Object.DestroyImmediate(go);
   float worstOvershoot=0,worstFinalError=0;
   foreach(float mass in new[]{.05f,.2f,5f})
   {
    float x=0,v=0;
    for(int step=0;step<180;step++)
    {
     var force=HandGrabCoupling.Force(mass,Vector3.right*(.04f-x),Vector3.right*v);
     if(force.magnitude>mass*18.001f)throw new Exception("Grab force exceeds acceleration limit");
     v+=force.x/mass/120;x+=v/120;worstOvershoot=Mathf.Max(worstOvershoot,x-.04f);
    }
    worstFinalError=Mathf.Max(worstFinalError,Mathf.Abs(x-.04f));
   }
   if(worstOvershoot>.001f||worstFinalError>.001f)throw new Exception("Grab coupling oscillates or does not settle");
   Debug.Log($"[MGFR continuous hands checks] PASS physicsDynamicOnly=True rawVisualNoPrediction=True grabAccelerationLimit=18 grabOvershootMetres={worstOvershoot:F6} grabFinalErrorMetres={worstFinalError:F6}");
   OcclusionHandsBuild.Build();
  }
 }
}
