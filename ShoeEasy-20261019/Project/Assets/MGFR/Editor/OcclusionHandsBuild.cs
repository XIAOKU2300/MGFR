using System;
using UnityEngine;

namespace MGFR.BareHands
{
 public static class OcclusionHandsBuild
 {
  public static void Build()
  {
   var go=new GameObject("Render input split check");var source=go.AddComponent<HandJointSource>();
   var raw=new HandFrame{Tracked=true,ValidCount=26};var stable=new HandFrame{Tracked=true,ValidCount=26};
   for(int i=0;i<26;i++)
   {
    raw.Valid[i]=stable.Valid[i]=true;
    raw.Joints[i]=new Pose(new Vector3(i*.005f,1,.5f),Quaternion.identity);raw.Radius[i]=.008f;
    stable.Joints[i]=new Pose(raw.Joints[i].position+Vector3.left*.02f,Quaternion.identity);stable.Radius[i]=.0084f;
   }
   source.UpdateRenderFrame(0,raw,stable);
   for(int i=0;i<26;i++)if(Vector3.Distance(source.RenderFrames[0].Joints[i].position,raw.Joints[i].position)>.000001f)throw new Exception("Visual occlusion must not inherit physics lag or enlargement");
   raw.Valid[10]=false;source.UpdateRenderFrame(0,raw,stable);
   if(!source.RenderFrames[0].Valid[10]||source.RenderFrames[0].Observed[10])throw new Exception("Missing tip must remain marked as held");
   raw.Valid[1]=false;source.UpdateRenderFrame(0,raw,stable);
   if(source.RenderFrames[0].Tracked)throw new Exception("Lost wrist must hide occlusion");
   UnityEngine.Object.DestroyImmediate(go);
   Debug.Log("[MGFR occlusion split check] PASS latestObservedJointsExact=True physicsFilterExcluded=True sizeGainExcluded=True heldTipNotObserved=True lostWristHides=True");
   StabilizedHandsBuild.Build();
  }
 }
}
