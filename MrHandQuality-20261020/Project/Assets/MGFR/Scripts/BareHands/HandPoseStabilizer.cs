using System;
using UnityEngine;

namespace MGFR.BareHands
{
 public sealed class HandPoseStabilizer
 {
  // Finger filtering is relative to the wrist, so hand movement does not drag the fingers behind it.
  static readonly int[] Parent={1,-1,1,2,3,4,1,6,7,8,9,1,11,12,13,14,1,16,17,18,19,1,21,22,23,24};
  readonly Vector3[] previousRaw=new Vector3[26],position=new Vector3[26],speed=new Vector3[26];
  readonly Quaternion[] rotation=new Quaternion[26],previousRotation=new Quaternion[26];
  readonly double[] lastSeen=new double[26],lastFilter=new double[26];
  readonly bool[] initialized=new bool[26];
  readonly float[] length=new float[26],radii=new float[26];
  public const float SizeGain=1f;
  double previousHand;
  public int HeldJoints {get;private set;}
  public void Reset(){Array.Clear(initialized,0,26);Array.Clear(length,0,26);HeldJoints=0;previousHand=0;}
  static float Alpha(float cutoff,float dt)=>1f/(1f+1f/(2f*Mathf.PI*cutoff*dt));

  void Smooth(int i,Vector3 p,Quaternion q,double now)
  {
   if(!initialized[i]){position[i]=previousRaw[i]=p;rotation[i]=previousRotation[i]=q;initialized[i]=true;speed[i]=Vector3.zero;}
   else
   {
    float dt=Mathf.Clamp((float)(now-lastFilter[i]),.001f,.05f);
    var derivative=(p-previousRaw[i])/dt;speed[i]=Vector3.Lerp(speed[i],derivative,Alpha(1,dt));
    position[i]=Vector3.Lerp(position[i],p,Alpha((i==1?8:3.5f)+25*speed[i].magnitude,dt));
    float angularSpeed=Quaternion.Angle(previousRotation[i],q)/dt;
    rotation[i]=Quaternion.Slerp(rotation[i],q,Alpha((i==1?10:5)+.025f*angularSpeed,dt));
    previousRaw[i]=p;previousRotation[i]=q;
   }
   lastFilter[i]=lastSeen[i]=now;
  }

  public void Process(HandFrame raw,HandFrame result,double now)
  {
   result.Clear();result.Timestamp=raw.Timestamp;result.ReceivedAt=raw.ReceivedAt;result.UnityFrame=raw.UnityFrame;result.UpdatePhase=raw.UpdatePhase;HeldJoints=0;
   if(!raw.Valid[1]){Reset();return;}
   if(previousHand>0&&now-previousHand>.1)Reset();previousHand=now;
   var wrist=raw.Joints[1];var inverse=Quaternion.Inverse(wrist.rotation);
   Smooth(1,wrist.position,wrist.rotation,now);
   for(int step=0;step<26;step++)
   {
    int i=step==0?1:step==1?0:step;
    bool observed=raw.Valid[i];
    if(i!=1&&observed)
    {
     var p=inverse*(raw.Joints[i].position-wrist.position);
     var q=inverse*raw.Joints[i].rotation;
     Smooth(i,p,q,now);
    }
    if(!initialized[i]||(!observed&&now-lastSeen[i]>.06))continue;
    if(!observed)HeldJoints++;
    Vector3 local=i==1?Vector3.zero:position[i];
    int parent=Parent[i];
    if(i!=1&&parent>=0&&result.Valid[parent])
    {
     Vector3 parentLocal=parent==1?Vector3.zero:position[parent];
     float measured=raw.Valid[i]&&raw.Valid[parent]?Vector3.Distance(raw.Joints[i].position,raw.Joints[parent].position):0;
     if(measured>.003f&&measured<.13f)
     {
      if(length[i]==0)length[i]=measured;
      else if(measured>length[i]*.8f&&measured<length[i]*1.2f)length[i]=Mathf.Lerp(length[i],measured,.015f);
     }
     var segment=local-parentLocal;
     if(length[i]>0&&segment.sqrMagnitude>.000001f)local=parentLocal+segment.normalized*length[i];
     position[i]=local;
    }
    result.Joints[i]=i==1?new Pose(position[1],rotation[1]):new Pose(position[1]+rotation[1]*local,rotation[1]*rotation[i]);
    result.Valid[i]=true;result.Observed[i]=observed;result.ValidCount++;
    if(observed)result.ObservedCount++;
    if(observed)radii[i]=raw.Radius[i];
    result.Radius[i]=radii[i]*SizeGain;
    result.LastValidTime[i]=(float)lastSeen[i];result.JointSource[i]=observed?JointSampleSource.SDK:JointSampleSource.Held;
    result.RadiusSource[i]=raw.RadiusSource[i];
   }
   var anchor=result.Joints[1].position;
   for(int i=0;i<26;i++)if(result.Valid[i])result.Joints[i].position=anchor+(result.Joints[i].position-anchor)*SizeGain;
   result.Tracked=result.ValidCount>=20&&result.Valid[0]&&result.Valid[1]&&result.Valid[7]&&result.Valid[12]&&result.Valid[17]&&result.Valid[22];
  }
 }
}
