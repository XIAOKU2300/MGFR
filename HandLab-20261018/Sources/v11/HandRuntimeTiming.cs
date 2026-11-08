using UnityEngine;

namespace MGFR.BareHands
{
 public sealed class HandRuntimeTiming:MonoBehaviour
 {
  BareHandInteraction hands;float next=5,totalFrame,maxFrame,totalPhysics,maxPhysics;int samples,slowFrames;
  void Start(){hands=GetComponent<BareHandInteraction>();}
  void Update()
  {
   if(!hands.IsReady||hands.Source.Replay)return;
   float frame=Time.unscaledDeltaTime*1000,physics=hands.Physics.LastMilliseconds;
   totalFrame+=frame;maxFrame=Mathf.Max(maxFrame,frame);totalPhysics+=physics;maxPhysics=Mathf.Max(maxPhysics,physics);samples++;
   if(frame>28)slowFrames++;
   if(Time.unscaledTime<next)return;next=Time.unscaledTime+5;
   Debug.Log($"[MGFR hand timing] frameMeanMs={totalFrame/samples:F2} frameMaxMs={maxFrame:F2} framesOver28ms={slowFrames}/{samples} physicsMeanMs={totalPhysics/samples:F2} physicsMaxMs={maxPhysics:F2} dynamicCallbacks={hands.Source.DynamicCallbacks} beforeRenderCallbacks={hands.Source.RenderCallbacks} nativeTrackingLosses={hands.Source.TrackingLosses} missingJointUpdates={hands.Source.MissingUpdates} colliderStateChanges={hands.ColliderStateChanges} substepPoseWrites={hands.SubstepPoseWrites}; callback counts are not camera latency or recognition confidence");
   samples=slowFrames=0;totalFrame=maxFrame=totalPhysics=maxPhysics=0;
  }
 }
}
