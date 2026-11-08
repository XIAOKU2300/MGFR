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
  public bool Tracked;public int ValidCount;public float Timestamp;
  public Vector3 PinchPoint=>(Joints[5].position+Joints[10].position)*.5f;
  public float Scale=>Mathf.Clamp(Vector3.Distance(Joints[1].position,Joints[12].position)/.08f,.65f,1.45f);
  public void Clear(){Tracked=false;ValidCount=0;Array.Clear(Valid,0,26);}
 }
 public sealed class HandJointSource:MonoBehaviour
 {
  public readonly HandFrame[] Frames={new HandFrame(),new HandFrame()};
  public bool Replay {get;set;}
  public bool Running=>subsystem!=null&&subsystem.running;
  public bool ExtensionEnabled=>OpenXRRuntime.IsExtensionEnabled("XR_EXT_hand_tracking");
  public event Action BeforeRenderData;
  XRHandSubsystem subsystem;readonly List<XRHandSubsystem> systems=new List<XRHandSubsystem>();
  Transform origin;float nextScan;
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
   for(int h=0;h<2;h++)if(!Running||Time.unscaledTime-Frames[h].Timestamp>.15f)Frames[h].Clear();
  }
  void OnHands(XRHandSubsystem s,XRHandSubsystem.UpdateSuccessFlags flags,XRHandSubsystem.UpdateType type)
  {
   if(Replay)return;
   Read(s.leftHand,Frames[0],(flags&XRHandSubsystem.UpdateSuccessFlags.LeftHandJoints)!=0);
   Read(s.rightHand,Frames[1],(flags&XRHandSubsystem.UpdateSuccessFlags.RightHandJoints)!=0);
   if(type==XRHandSubsystem.UpdateType.BeforeRender)BeforeRenderData?.Invoke();
  }
  void Read(XRHand hand,HandFrame f,bool updated)
  {
   f.Clear();f.Timestamp=Time.unscaledTime;if(!hand.isTracked||!updated)return;
   for(int i=0;i<26;i++)
   {
    var joint=hand.GetJoint(Ids[i]);
    if(!joint.TryGetPose(out var pose))continue;
    f.Joints[i]=new Pose(origin.TransformPoint(pose.position),origin.rotation*pose.rotation);
    f.Valid[i]=true;f.ValidCount++;
    f.Radius[i]=joint.TryGetRadius(out float r)?Mathf.Clamp(r,.004f,.02f):.008f;
   }
   f.Tracked=f.ValidCount>=20&&f.Valid[0]&&f.Valid[1]&&f.Valid[7]&&f.Valid[12]&&f.Valid[17]&&f.Valid[22];
  }
  public void SetReplayFrame(int hand,Pose[] joints,bool tracked)
  {
   Replay=true;var f=Frames[hand];f.Clear();f.Timestamp=Time.unscaledTime;
   if(!tracked)return;
   for(int i=0;i<26;i++){f.Joints[i]=joints[i];f.Radius[i]=i<2?.018f:.008f;f.Valid[i]=true;}
   f.Tracked=true;f.ValidCount=26;
  }
  void OnDestroy(){if(subsystem!=null)subsystem.updatedHands-=OnHands;}
 }
}
