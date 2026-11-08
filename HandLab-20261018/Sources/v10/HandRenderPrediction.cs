using System;
using UnityEngine;

namespace MGFR.BareHands
{
 public sealed class HandRenderPrediction
 {
  public const float LeadSeconds=.018f;
  readonly Pose[] previous=new Pose[26],sample=new Pose[26],forecast=new Pose[26];
  readonly Vector3[] previousVelocity=new Vector3[26],velocity=new Vector3[26],previousAngular=new Vector3[26],angular=new Vector3[26];
  readonly double[] sampleTime=new double[26];readonly bool[] have=new bool[26];
  static readonly int[] Parent={1,-1,1,2,3,4,1,6,7,8,9,1,11,12,13,14,1,16,17,18,19,1,21,22,23,24};
  public void Reset(){Array.Clear(have,0,26);}
  Pose Predict(int i,Pose raw,double now)
  {
   if(!have[i]||now-sampleTime[i]>.075)
   {
    have[i]=true;previous[i]=raw;sampleTime[i]=now;
    previousVelocity[i]=velocity[i]=previousAngular[i]=angular[i]=Vector3.zero;return raw;
   }
   float dt=(float)(now-sampleTime[i]);
   bool changed=Vector3.Distance(raw.position,previous[i].position)>.00001f||Quaternion.Angle(raw.rotation,previous[i].rotation)>.01f;
   if(dt>=.004f&&(changed||dt>=.009f))
   {
    var measured=(raw.position-previous[i].position)/dt;
    velocity[i]=measured.magnitude>.04f&&Vector3.Dot(measured,previousVelocity[i])>0?(measured+previousVelocity[i])*.5f:Vector3.zero;
    var delta=raw.rotation*Quaternion.Inverse(previous[i].rotation);delta.ToAngleAxis(out float angle,out var axis);if(angle>180)angle-=360;
    var measuredAngular=axis*(angle/dt);
    angular[i]=measuredAngular.magnitude>20&&Vector3.Dot(measuredAngular,previousAngular[i])>0?(measuredAngular+previousAngular[i])*.5f:Vector3.zero;
    previousVelocity[i]=measured;previousAngular[i]=measuredAngular;previous[i]=raw;sampleTime[i]=now;
   }
   float horizon=i==1?LeadSeconds:LeadSeconds*.5f;
   var offset=Vector3.ClampMagnitude(velocity[i]*horizon,i==1?.025f:.006f);
   float degrees=Mathf.Min(angular[i].magnitude*horizon,i==1?8:5);
   var turn=degrees>.0001f?Quaternion.AngleAxis(degrees,angular[i].normalized):Quaternion.identity;
   return new Pose(raw.position+offset,turn*raw.rotation);
  }
  public void Apply(HandFrame frame,double now)
  {
   if(!frame.Tracked||!frame.Observed[1]){Reset();return;}
   var wrist=frame.Joints[1];var inverse=Quaternion.Inverse(wrist.rotation);
   for(int i=0;i<26;i++)sample[i]=frame.Joints[i];
   var nextWrist=Predict(1,wrist,now);forecast[1]=nextWrist;
   for(int i=0;i<26;i++)
   {
    if(i==1||!frame.Valid[i])continue;
    var local=new Pose(inverse*(sample[i].position-wrist.position),inverse*sample[i].rotation);
    var next=frame.Observed[i]?Predict(i,local,now):local;
    forecast[i]=new Pose(nextWrist.position+nextWrist.rotation*next.position,nextWrist.rotation*next.rotation);
   }
   // Keep the observed bone lengths while predicting flexion; never stretch fingers to gain speed.
   for(int step=0;step<26;step++)
   {
    int i=step==0?1:step==1?0:step;if(!frame.Valid[i])continue;
    int parent=Parent[i];
    if(parent>=0&&frame.Valid[parent])
    {
     var direction=forecast[i].position-forecast[parent].position;
     if(direction.sqrMagnitude>.000001f)forecast[i].position=forecast[parent].position+direction.normalized*Vector3.Distance(sample[i].position,sample[parent].position);
    }
    frame.Joints[i]=forecast[i];
   }
  }
 }
}
