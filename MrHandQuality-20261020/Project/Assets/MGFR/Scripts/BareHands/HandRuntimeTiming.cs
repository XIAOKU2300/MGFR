using UnityEngine;

namespace MGFR.BareHands
{
 public sealed class HandRuntimeTiming:MonoBehaviour
 {
  BareHandInteraction hands;float next=5,totalFrame,maxFrame,totalPhysics,maxPhysics;int samples,slowFrames;
  readonly System.Collections.Generic.List<float> frameTimes=new System.Collections.Generic.List<float>(1024);
  float renderTotal;uint previousDrops;
  void Start(){hands=GetComponent<BareHandInteraction>();}
  void Update()
  {
   if(!hands.IsReady||hands.Source.Replay)return;
   float frame=Time.unscaledDeltaTime*1000,physics=hands.Physics.LastMilliseconds;
   totalFrame+=frame;maxFrame=Mathf.Max(maxFrame,frame);totalPhysics+=physics;maxPhysics=Mathf.Max(maxPhysics,physics);samples++;
   if(frameTimes.Count<4096)frameTimes.Add(frame);
   renderTotal+=hands.DepthMeshes[0].LastRenderMilliseconds+hands.DepthMeshes[1].LastRenderMilliseconds;
   if(frame>28)slowFrames++;
   if(Time.unscaledTime<next)return;next=Time.unscaledTime+5;
   frameTimes.Sort();UnityEngine.XR.XRStats.TryGetDroppedFrameCount(out int dropped);
   Debug.Log($"[MR performance] frameMedianMs={frameTimes[frameTimes.Count/2]:F3} frameP95Ms={frameTimes[Mathf.Min(frameTimes.Count-1,(int)(frameTimes.Count*.95f))]:F3} handRenderCpuMeanMs={renderTotal/samples:F4} xrDroppedFrames={dropped} sampleCount={samples} rejectedJoints={hands.Source.RejectedJoints} relocationEvents={hands.Source.Relocations}; compare only same device/workload, not a headset acceptance");
   Debug.Log($"[MGFR hand timing] frameMeanMs={totalFrame/samples:F2} frameMaxMs={maxFrame:F2} framesOver28ms={slowFrames}/{samples} physicsMeanMs={totalPhysics/samples:F2} physicsMaxMs={maxPhysics:F2} dynamicCallbacks={hands.Source.DynamicCallbacks} beforeRenderCallbacks={hands.Source.RenderCallbacks} nativeTrackingLosses={hands.Source.TrackingLosses} missingJointUpdates={hands.Source.MissingUpdates} colliderStateChanges={hands.ColliderStateChanges} substepContactUpdates={hands.SubstepContactUpdates}; callback counts are not camera latency or recognition confidence");
   samples=slowFrames=0;totalFrame=maxFrame=totalPhysics=maxPhysics=renderTotal=0;frameTimes.Clear();
  }
 }
}
