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
  public bool CanStartPinch=>Observed[5]&&Observed[10];
  public bool Tracked;public int ValidCount;public float Timestamp;
  public Vector3 PinchPoint=>(Joints[5].position+Joints[10].position)*.5f;
  public float Scale=>Mathf.Clamp(Vector3.Distance(Joints[1].position,Joints[12].position)/.08f,.65f,1.45f);
  public void Clear(){Tracked=false;ValidCount=ObservedCount=0;Array.Clear(Valid,0,26);Array.Clear(Observed,0,26);}
 }
 public sealed class HandJointSource:MonoBehaviour
 {
  public readonly HandFrame[] Frames={new HandFrame(),new HandFrame()};
  public readonly HandFrame[] RenderFrames={new HandFrame(),new HandFrame()};
  public bool Replay {get;set;}
  public bool Running=>subsystem!=null&&subsystem.running;
  public bool ExtensionEnabled=>OpenXRRuntime.IsExtensionEnabled("XR_EXT_hand_tracking");
  public event Action BeforeRenderData;
  XRHandSubsystem subsystem;readonly List<XRHandSubsystem> systems=new List<XRHandSubsystem>();
  Transform origin;float nextScan;
  public bool PredictVisual=true;
  readonly HandRenderPrediction[] visualPrediction={new HandRenderPrediction(),new HandRenderPrediction()};
  readonly HandPoseStabilizer[] filters={new HandPoseStabilizer(),new HandPoseStabilizer()};
  readonly HandFrame raw=new HandFrame();
  static readonly XRHandJointID[] Ids={XRHandJointID.Palm,XRHandJointID.Wrist,
   XRHandJointID.ThumbMetacarpal,XRHandJointID.ThumbProximal,XRHandJointID.ThumbDistal,XRHandJointID.ThumbTip,
   XRHandJointID.IndexMetacarpal,XRHandJointID.IndexProximal,XRHandJointID.IndexIntermediate,XRHandJointID.IndexDistal,XRHandJointID.IndexTip,
   XRHandJointID.MiddleMetacarpal,XRHandJointID.MiddleProximal,XRHandJointID.MiddleIntermediate,XRHandJointID.MiddleDistal,XRHandJointID.MiddleTip,
   XRHandJointID.RingMetacarpal,XRHandJointID.RingProximal,XRHandJointID.RingIntermediate,XRHandJointID.RingDistal,XRHandJointID.RingTip,
   XRHandJointID.LittleMetacarpal,XRHandJointID.LittleProximal,XRHandJointID.LittleIntermediate,XRHandJointID.LittleDistal,XRHandJointID.LittleTip};
  void Start(){origin=Camera.main.transform.parent;}
  void Update()
  {
   if(Replay)return;
   if(Input.GetKeyDown(KeyCode.F10)){PredictVisual=!PredictVisual;foreach(var p in visualPrediction)p.Reset();Debug.Log("[MGFR hand response] visualPrediction="+PredictVisual+" horizonMs=18; F10 compare");}
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
   for(int h=0;h<2;h++)if(!Running||Time.unscaledTime-Frames[h].Timestamp>.1f){Frames[h].Clear();RenderFrames[h].Clear();filters[h].Reset();visualPrediction[h].Reset();}
  }
  void OnHands(XRHandSubsystem s,XRHandSubsystem.UpdateSuccessFlags flags,XRHandSubsystem.UpdateType type)
  {
   if(Replay)return;
   Read(0,s.leftHand,Frames[0],(flags&XRHandSubsystem.UpdateSuccessFlags.LeftHandJoints)!=0);
   Read(1,s.rightHand,Frames[1],(flags&XRHandSubsystem.UpdateSuccessFlags.RightHandJoints)!=0);
   if(type==XRHandSubsystem.UpdateType.BeforeRender)BeforeRenderData?.Invoke();
  }
  void Read(int h,XRHand hand,HandFrame f,bool updated)
  {
   if(!hand.isTracked){f.Clear();RenderFrames[h].Clear();filters[h].Reset();visualPrediction[h].Reset();return;}
   if(!updated)return;
   raw.Clear();raw.Timestamp=Time.unscaledTime;
   for(int i=0;i<26;i++)
   {
    var joint=hand.GetJoint(Ids[i]);
    if(!joint.TryGetPose(out var pose))continue;
    raw.Joints[i]=new Pose(origin.TransformPoint(pose.position),origin.rotation*pose.rotation);
    raw.Valid[i]=true;raw.ValidCount++;
    raw.Radius[i]=joint.TryGetRadius(out float r)?Mathf.Clamp(r,.004f,.02f):.008f;
   }
   filters[h].Process(raw,f,Time.realtimeSinceStartupAsDouble);
   UpdateRenderFrame(h,raw,f);
   if(PredictVisual)visualPrediction[h].Apply(RenderFrames[h],Time.realtimeSinceStartupAsDouble);
  }
  // Visual occlusion follows the freshest SDK sample, independent of physics smoothing and size gain.
  public void UpdateRenderFrame(int h,HandFrame observed,HandFrame stable)
  {
   var target=RenderFrames[h];target.Clear();target.Timestamp=observed.Timestamp;
   if(!observed.Valid[1])return;
   var wrist=observed.Joints[1];var inverse=Quaternion.Inverse(stable.Joints[1].rotation);
   for(int i=0;i<26;i++)
   {
    if(observed.Valid[i])
    {
     target.Joints[i]=observed.Joints[i];target.Radius[i]=observed.Radius[i];target.Observed[i]=true;target.ObservedCount++;
    }
    else if(stable.Valid[i])
    {
     var relative=inverse*(stable.Joints[i].position-stable.Joints[1].position)/HandPoseStabilizer.SizeGain;
     target.Joints[i]=new Pose(wrist.position+wrist.rotation*relative,wrist.rotation*inverse*stable.Joints[i].rotation);
     target.Radius[i]=stable.Radius[i]/HandPoseStabilizer.SizeGain;
    }
    else continue;
    target.Valid[i]=true;target.ValidCount++;
   }
   target.Tracked=target.ValidCount>=20&&target.Valid[0]&&target.Valid[1]&&target.Valid[7]&&target.Valid[12]&&target.Valid[17]&&target.Valid[22];
  }
  public void SetReplayFrame(int hand,Pose[] joints,bool tracked)
  {
   Replay=true;var f=Frames[hand];f.Clear();f.Timestamp=Time.unscaledTime;
   if(!tracked){RenderFrames[hand].Clear();return;}
   for(int i=0;i<26;i++){f.Joints[i]=joints[i];f.Radius[i]=i<2?.018f:.008f;f.Valid[i]=true;}
   f.Tracked=true;f.ValidCount=f.ObservedCount=26;for(int i=0;i<26;i++)f.Observed[i]=true;
   UpdateRenderFrame(hand,f,f);
  }
  void OnDestroy(){if(subsystem!=null)subsystem.updatedHands-=OnHands;}
 }
}
