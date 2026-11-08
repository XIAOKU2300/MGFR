using System;
using UnityEngine;
using MGFR.BareHands;

namespace MGFR.GesturePanel {
 public static class HandMenuPose {
  static readonly int[] Required={0,1,3,4,5,7,8,9,10,12,13,14,15,17,18,19,20,22,23,24,25};
  static readonly int[] Knuckles={7,12,17,22};
  public static bool Fresh(HandFrame f,float now){
   if(f==null||!f.Tracked||!float.IsFinite(f.Timestamp)||now-f.Timestamp>.085f||f.Timestamp-now>.025f)return false;
   foreach(int j in Required)if(!f.Valid[j]||!f.Observed[j]||!float.IsFinite(f.Joints[j].position.sqrMagnitude))return false;
   return true;
  }
  public static float PalmLength(HandFrame f)=>Mathf.Clamp(Vector3.Distance(f.Joints[1].position,f.Joints[12].position),.045f,.14f);
  static float Curl(HandFrame f,int k){var first=f.Joints[k+1].position-f.Joints[k].position;var last=f.Joints[k+3].position-f.Joints[k+2].position;return first.sqrMagnitude>1e-7f&&last.sqrMagnitude>1e-7f?Vector3.Angle(first,last):0;}
  public static bool Fist(HandFrame f){
   float palm=PalmLength(f);var center=f.Joints[0].position;
   foreach(int k in Knuckles)if(Curl(f,k)<65||Vector3.Distance(f.Joints[k+3].position,center)>palm*.95f)return false;
   return Vector3.Distance(f.Joints[5].position,center)<palm*1.02f&&Vector3.Distance(f.Joints[5].position,f.Joints[7].position)<palm;
  }
  public static bool Open(HandFrame f){int extended=0;float palm=PalmLength(f);foreach(int k in Knuckles)if(Curl(f,k)<35&&Vector3.Distance(f.Joints[k+3].position,f.Joints[1].position)>palm*1.45f)extended++;return extended>=3;}
  // Summoning needs the whole fist; touching only needs a live wrist/index.
  // Other curled or temporarily occluded fingers must not disable a visible tip.
  public static bool FreshTouch(HandFrame f,float now){
   if(f==null||!f.Tracked||!float.IsFinite(f.Timestamp)||now-f.Timestamp>.10f||f.Timestamp-now>.025f)return false;
   foreach(int j in new[]{1,7,8,9,10})if(!f.Valid[j]||!float.IsFinite(f.Joints[j].position.sqrMagnitude))return false;
   return f.Observed[1]&&f.Observed[7]&&f.Observed[10];
  }
  public static bool Pointer(HandFrame f){
   float scale=f.Valid[1]&&f.Valid[12]?PalmLength(f)/.08f:1;
   if(Curl(f,7)>70||Vector3.Distance(f.Joints[7].position,f.Joints[10].position)<.028f*scale)return false;
   return !f.Valid[5]||!f.Observed[5]||Vector3.Distance(f.Joints[5].position,f.Joints[10].position)>.012f;
  }
 }

 public sealed class FistSummonGate {
  public bool Armed {get;private set;}
  public float Progress {get;private set;}
  public int Fires {get;private set;}
  public string Reason {get;private set;}="先张开手掌";
  float openSince=-1,holdSince=-1,lastSample=-1,lastNow=-1,cooldown,velocity;
  Vector3 palm;
  public void Reset(bool requireOpen=true){holdSince=openSince=-1;Progress=0;if(requireOpen)Armed=false;}
  public void Closed(float now){Reset();cooldown=now+1.0f;}
  public bool Step(HandFrame frame,float now,bool native,bool blocked,bool menuOpen){
   Progress=0;
   if(!native||!HandMenuPose.Fresh(frame,now)||blocked||menuOpen||now<cooldown){
    Reason=!native?"需要真实手部追踪":blocked?"先离开角色并松开物品":menuOpen?"面板已展开":"先张开手掌";
    Reset();lastSample=-1;lastNow=now;return false;
   }
   if(lastNow>=0&&(now<lastNow||now-lastNow>.1f)){Reset();lastSample=-1;}lastNow=now;
   if(frame.Timestamp<=lastSample){if(holdSince>=0)Progress=Mathf.Clamp01((now-holdSince)/3);return false;}
   float dt=lastSample<0?0:frame.Timestamp-lastSample;
   if(dt>.085f){Reset();velocity=0;}
   if(dt>0){float speed=Vector3.Distance(frame.Joints[0].position,palm)/dt;velocity=Mathf.Lerp(velocity,speed,1-Mathf.Exp(-dt/0.1f));}
   palm=frame.Joints[0].position;lastSample=frame.Timestamp;
   if(HandMenuPose.Open(frame)){
    holdSince=-1;if(openSince<0)openSince=now;if(now-openSince>=.25f)Armed=true;
    Reason=Armed?"握拳保持超过3秒唤出":"先张开手掌";return false;
   }
   openSince=-1;
   if(!Armed){Reason="先张开手掌";holdSince=-1;return false;}
   if(!HandMenuPose.Fist(frame)||velocity>.18f){holdSince=-1;Reason=velocity>.18f?"保持手部稳定":"四指收拢并握拳";return false;}
   if(holdSince<0)holdSince=now;Progress=Mathf.Clamp01((now-holdSince)/3);Reason="握拳保持";
   if(now-holdSince<=3f)return false;
   Fires++;Closed(now);return true;
  }
 }

 public sealed class FingerTouchGate {
  public bool Armed {get;private set;}
  public int Hovered {get;private set;}=-1;
  public float Compression {get;private set;}
  public int Fires {get;private set;}
  bool latched,hadPoint;float contactSince=-1,lastSample=-1;int contactTarget=-1;Vector3 previous;
  public void Reset(){Armed=latched=hadPoint=false;Hovered=-1;Compression=0;contactSince=lastSample=-1;contactTarget=-1;}
  static float Radius(float radius)=>float.IsFinite(radius)?Mathf.Clamp(radius,.004f,.016f):.008f;
  public Vector2 ContactPoint(Vector3 tip,float radius,float surfaceZ,float sampleTime){
   float plane=surfaceZ-Radius(radius)+.001f;
   if(hadPoint&&sampleTime>lastSample&&sampleTime-lastSample<=.10f&&Vector3.Distance(tip,previous)<=.25f&&previous.z<plane&&tip.z>=plane){
    var crossing=Vector3.Lerp(previous,tip,Mathf.Clamp01((plane-previous.z)/(tip.z-previous.z)));return new Vector2(crossing.x,crossing.y);
   }return new Vector2(tip.x,tip.y);
  }
  public int Step(bool valid,float sampleTime,Vector3 tip,float radius,int hit,float surfaceZ,float now,float holdSeconds=0){
   Hovered=-1;Compression=0;
   if(!valid||!float.IsFinite(tip.sqrMagnitude)||!float.IsFinite(sampleTime)||now-sampleTime>.10f||sampleTime-now>.025f){Reset();return -1;}
   if(sampleTime<=lastSample)return -1;
   if(hadPoint&&(sampleTime-lastSample>.10f||Vector3.Distance(tip,previous)>.25f))Reset();
   bool continuous=hadPoint;float previousZ=hadPoint?previous.z:tip.z;previous=tip;hadPoint=true;lastSample=sampleTime;
   radius=Radius(radius);float plane=surfaceZ-radius+.001f;
   if(tip.z<surfaceZ-radius-.010f){
    Armed=true;latched=false;contactSince=-1;contactTarget=-1;
    if(hit>=0&&surfaceZ-tip.z<.055f)Hovered=hit;return -1;
   }
   if(latched||!Armed)return -1;
   if(hit<0){contactSince=-1;contactTarget=-1;return -1;}
   Hovered=hit;Compression=Mathf.Clamp01((tip.z+radius-surfaceZ+.003f)/.011f);
   if(contactSince<0){
    // Sweep through the front plane: a fast poke may already be behind the
    // whole panel on the next sample. Ordinary switches fire on this sample.
    if(!continuous||previousZ>=plane||tip.z<plane)return -1;
    contactSince=now;contactTarget=hit;
   }
   if(contactTarget!=hit||tip.z<plane-.004f){contactSince=-1;contactTarget=-1;Armed=false;return -1;}
   if(holdSeconds>0&&tip.z>surfaceZ+.035f){contactSince=-1;contactTarget=-1;Armed=false;return -1;}
   if(now-contactSince<holdSeconds)return -1;
   latched=true;Armed=false;Fires++;return hit;
  }
 }
}
