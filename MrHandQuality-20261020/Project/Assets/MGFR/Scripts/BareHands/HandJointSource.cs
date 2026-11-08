using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR.Hands;
using UnityEngine.XR.OpenXR;

namespace MGFR.BareHands
{
 public sealed class HandFrame
 {
  public readonly Pose[] Joints=new Pose[26];
  public readonly float[] Radius=new float[26];
  public readonly bool[] Valid=new bool[26];
  public readonly bool[] Observed=new bool[26];public int ObservedCount;
  public readonly float[] LastValidTime=new float[26];
  public readonly JointSampleSource[] JointSource=new JointSampleSource[26];
  public readonly JointRadiusSource[] RadiusSource=new JointRadiusSource[26];
  public int UnityFrame; public double ReceivedAt; public string UpdatePhase="unknown";
  public bool CanStartPinch=>Tracked&&Valid[5]&&Valid[10]&&Observed[5]&&Observed[10];
  public bool Tracked;public int ValidCount;public float Timestamp;
  public Vector3 PinchPoint=>(Joints[5].position+Joints[10].position)*.5f;
  public float Scale=>Mathf.Clamp(Vector3.Distance(Joints[1].position,Joints[12].position)/.08f,.65f,1.8f);
  public void Clear(){Tracked=false;ValidCount=ObservedCount=0;Array.Clear(Valid,0,26);Array.Clear(Observed,0,26);Array.Clear(JointSource,0,26);Array.Clear(LastValidTime,0,26);Array.Clear(RadiusSource,0,26);}
 }
 public sealed class HandJointSource:MonoBehaviour
 {
  public readonly HandFrame[] Frames={new HandFrame(),new HandFrame()};
  public readonly HandFrame[] RenderFrames={new HandFrame(),new HandFrame()};
  public bool Replay {get;set;}
  // Native samples and render poses remain live regardless of interaction source.
  public readonly HandFrame[] NativeFrames={new HandFrame(),new HandFrame()};
  readonly bool[] controllerPose=new bool[2];
  public bool ControllerDriven=>controllerPose[0]||controllerPose[1];
  public bool IsControllerPose(int hand)=>controllerPose[hand];
  public string InputLabel(int hand)=>controllerPose[hand]?"CONTROLLER":"NATIVE";
  public bool HasFreshNativePose(int hand)=>NativeFrames[hand].Tracked&&Time.unscaledTime-NativeFrames[hand].Timestamp<=.1f;
  public void UseControllerPose(int hand,bool value)
  {
   if(controllerPose[hand]==value)return;controllerPose[hand]=value;
   if(!value&&HasFreshNativePose(hand))CopyFrame(NativeFrames[hand],Frames[hand]);else Frames[hand].Clear();
  }
  public static void CopyFrame(HandFrame from,HandFrame to)
  {
   to.Tracked=from.Tracked;to.ValidCount=from.ValidCount;to.ObservedCount=from.ObservedCount;to.Timestamp=from.Timestamp;
   Array.Copy(from.Joints,to.Joints,26);Array.Copy(from.Radius,to.Radius,26);
   Array.Copy(from.LastValidTime,to.LastValidTime,26);Array.Copy(from.JointSource,to.JointSource,26);Array.Copy(from.RadiusSource,to.RadiusSource,26);
   to.UnityFrame=from.UnityFrame;to.ReceivedAt=from.ReceivedAt;to.UpdatePhase=from.UpdatePhase;
   Array.Copy(from.Valid,to.Valid,26);Array.Copy(from.Observed,to.Observed,26);
  }
  public bool Running=>subsystem!=null&&subsystem.running;
  public bool ExtensionEnabled=>OpenXRRuntime.IsExtensionEnabled("XR_EXT_hand_tracking");
  public event Action BeforeRenderData;
  XRHandSubsystem subsystem;readonly List<XRHandSubsystem> systems=new List<XRHandSubsystem>();
  Transform origin;float nextScan;
  public int PhysicsSamples,DynamicCallbacks,RenderCallbacks,TrackingLosses,MissingUpdates;
  readonly HandPoseStabilizer[] filters={new HandPoseStabilizer(),new HandPoseStabilizer()};
  readonly HandFrame raw=new HandFrame();
  readonly HandSampleQuality[] quality={new HandSampleQuality(),new HandSampleQuality()};
  public readonly float[] LastBeforeRender={-100,-100};
  readonly HandFrame diagnosticRaw=new HandFrame();
  HandTrackingDiagnostics diagnostics;
  public int RejectedJoints=>quality[0].Rejected+quality[1].Rejected;
  public int Relocations=>quality[0].Relocations+quality[1].Relocations;
  static readonly XRHandJointID[] Ids={XRHandJointID.Palm,XRHandJointID.Wrist,
   XRHandJointID.ThumbMetacarpal,XRHandJointID.ThumbProximal,XRHandJointID.ThumbDistal,XRHandJointID.ThumbTip,
   XRHandJointID.IndexMetacarpal,XRHandJointID.IndexProximal,XRHandJointID.IndexIntermediate,XRHandJointID.IndexDistal,XRHandJointID.IndexTip,
   XRHandJointID.MiddleMetacarpal,XRHandJointID.MiddleProximal,XRHandJointID.MiddleIntermediate,XRHandJointID.MiddleDistal,XRHandJointID.MiddleTip,
   XRHandJointID.RingMetacarpal,XRHandJointID.RingProximal,XRHandJointID.RingIntermediate,XRHandJointID.RingDistal,XRHandJointID.RingTip,
   XRHandJointID.LittleMetacarpal,XRHandJointID.LittleProximal,XRHandJointID.LittleIntermediate,XRHandJointID.LittleDistal,XRHandJointID.LittleTip};
  void Start(){origin=Camera.main!=null?Camera.main.transform.parent:null;diagnostics=gameObject.AddComponent<HandTrackingDiagnostics>();}
  public void InvalidateHand(int h) {NativeFrames[h].Clear();RenderFrames[h].Clear();filters[h].Reset();quality[h].Reset();if(!controllerPose[h])Frames[h].Clear();}
  public void ExpireRender(float now) {for(int h=0;h<2;h++)if(now-RenderFrames[h].Timestamp>.06f)RenderFrames[h].Clear();}
  void Update()
  {
   if(Replay)return;
   if(Time.unscaledTime>=nextScan)
   {
    nextScan=Time.unscaledTime+.5f;SubsystemManager.GetSubsystems(systems);
    XRHandSubsystem found=null;foreach(var s in systems)if(s.running){found=s;break;}
    if(found!=subsystem)
    {
     if(subsystem!=null)subsystem.updatedHands-=OnHands;
     subsystem=found;if(subsystem!=null)subsystem.updatedHands+=OnHands;
     Debug.Log($"[MGFR hands] XR_EXT_hand_tracking={ExtensionEnabled}, subsystemRunning={Running}; joint poses require headset verification");
    }
   }
   for(int h=0;h<2;h++)
   {
    if(!Running||Time.unscaledTime-NativeFrames[h].Timestamp>.1f)
    {InvalidateHand(h);}
    if(!Running||Time.unscaledTime-RenderFrames[h].Timestamp>.06f)RenderFrames[h].Clear();
   }
  }
  void OnHands(XRHandSubsystem s,XRHandSubsystem.UpdateSuccessFlags flags,XRHandSubsystem.UpdateType type)
  {
   if(Replay)return;
   if(type==XRHandSubsystem.UpdateType.Dynamic)DynamicCallbacks++;else RenderCallbacks++;
   Read(0,s.leftHand,NativeFrames[0],(flags&XRHandSubsystem.UpdateSuccessFlags.LeftHandJoints)!=0,type);
   Read(1,s.rightHand,NativeFrames[1],(flags&XRHandSubsystem.UpdateSuccessFlags.RightHandJoints)!=0,type);
   if(type==XRHandSubsystem.UpdateType.BeforeRender)BeforeRenderData?.Invoke();
  }
  void Read(int h,XRHand hand,HandFrame f,bool updated,XRHandSubsystem.UpdateType type)
  {
   if(!hand.isTracked){if(f.Tracked||RenderFrames[h].Tracked)TrackingLosses++;InvalidateHand(h);return;}
   if(!updated){MissingUpdates++;if(type==XRHandSubsystem.UpdateType.BeforeRender)RenderFrames[h].Clear();return;}
   raw.Clear();raw.Timestamp=Time.unscaledTime;
   for(int i=0;i<26;i++)
   {
    var joint=hand.GetJoint(Ids[i]);
    if(!joint.TryGetPose(out var pose))continue;
    if(!float.IsFinite(pose.position.sqrMagnitude)||!float.IsFinite(pose.rotation.x)||!float.IsFinite(pose.rotation.y)||!float.IsFinite(pose.rotation.z)||!float.IsFinite(pose.rotation.w))continue;
    raw.Joints[i]=new Pose(origin!=null?origin.TransformPoint(pose.position):pose.position,origin!=null?origin.rotation*pose.rotation:pose.rotation);
    raw.Valid[i]=true;raw.ValidCount++;
    bool measured=joint.TryGetRadius(out float r)&&float.IsFinite(r)&&r>=.002f&&r<=.03f;
    raw.Radius[i]=measured?r:0;raw.RadiusSource[i]=measured?JointRadiusSource.Device:JointRadiusSource.Unknown;
   }
   // Missing provider radii scale with observed palm width, never a global pose gain.
   float width=raw.Valid[7]&&raw.Valid[22]?Vector3.Distance(raw.Joints[7].position,raw.Joints[22].position):.065f;
   for(int i=0;i<26;i++)if(raw.Valid[i]&&raw.Radius[i]<=0)
    {raw.Radius[i]=Mathf.Clamp(width*(i<2?.24f:i==5||i==10||i==15||i==20||i==25?.10f:.135f),.004f,.025f);raw.RadiusSource[i]=JointRadiusSource.PalmEstimate;}
   AcceptSample(h,raw,type,Time.realtimeSinceStartupAsDouble);
  }
  public void AcceptSample(int h,HandFrame sample,XRHandSubsystem.UpdateType type,double now)
  {
   sample.ReceivedAt=now;sample.UnityFrame=Time.frameCount;sample.UpdatePhase=type.ToString();
   if(diagnostics!=null&&diagnostics.Capturing)CopyFrame(sample,diagnosticRaw);
   // A coherent whole-hand relocation resets history, then uses the new measured
   // pose immediately. BareHandInteraction releases grabs and enforces its .10 s
   // recovery/open-hand gate on the discontinuity; no extrapolated bridge is drawn.
   if(quality[h].Filter(sample)){filters[h].Reset();NativeFrames[h].Clear();if(!controllerPose[h])Frames[h].Clear();RenderFrames[h].Clear();}
   if(type==XRHandSubsystem.UpdateType.BeforeRender)LastBeforeRender[h]=sample.Timestamp;
   if(type==XRHandSubsystem.UpdateType.Dynamic)
   {filters[h].Process(sample,NativeFrames[h],now);if(!controllerPose[h])CopyFrame(NativeFrames[h],Frames[h]);PhysicsSamples++;}
   UpdateRenderFrame(h,sample,NativeFrames[h]);
   if(diagnostics!=null&&diagnostics.Capturing)diagnostics.Capture(h,diagnosticRaw,NativeFrames[h],RenderFrames[h]);
  }
  // Visual occlusion follows the freshest SDK sample, independent of physics smoothing and size gain.
  public void UpdateRenderFrame(int h,HandFrame observed,HandFrame stable)
  {
   var target=RenderFrames[h];target.Clear();target.Timestamp=observed.Timestamp;
   if(!observed.Valid[1])return;
   target.ReceivedAt=observed.ReceivedAt;target.UnityFrame=observed.UnityFrame;target.UpdatePhase=observed.UpdatePhase;
   for(int i=0;i<26;i++)if(observed.Valid[i])
   {
    target.Joints[i]=observed.Joints[i];target.Radius[i]=observed.Radius[i];target.Valid[i]=target.Observed[i]=true;
    target.LastValidTime[i]=observed.LastValidTime[i];target.JointSource[i]=observed.JointSource[i];target.RadiusSource[i]=observed.RadiusSource[i];
    target.ValidCount++;target.ObservedCount++;
   }
   // Never reconstruct a missing visual tip from a filtered physics pose.
   target.Tracked=target.ValidCount>=8&&target.Valid[1];
  }

  public void PublishControllerFrame(int hand,Pose[] joints,bool tracked)
  {
   UseControllerPose(hand,true);var f=Frames[hand];f.Clear();f.Timestamp=Time.unscaledTime;
   if(!tracked||joints==null)return;
   // Interaction proxy only. Never overwrite native joints or their render pose.
   for(int i=0;i<26;i++)
   {f.Joints[i]=joints[i];f.Radius[i]=i<2?.018f:.008f;f.Valid[i]=f.Observed[i]=true;}
   f.Tracked=true;f.ValidCount=f.ObservedCount=26;
  }
  public void SetReplayFrame(int hand,Pose[] joints,bool tracked)
  {
   Replay=true;UseControllerPose(hand,false);var f=Frames[hand];f.Clear();f.Timestamp=Time.unscaledTime;
   if(!tracked){RenderFrames[hand].Clear();return;}
   for(int i=0;i<26;i++){f.Joints[i]=joints[i];f.Radius[i]=i<2?.018f:.008f;f.Valid[i]=true;}
   f.Tracked=true;f.ValidCount=f.ObservedCount=26;for(int i=0;i<26;i++)f.Observed[i]=true;
   UpdateRenderFrame(hand,f,f);
  }
  void OnDestroy(){if(subsystem!=null)subsystem.updatedHands-=OnHands;}
 }
}
