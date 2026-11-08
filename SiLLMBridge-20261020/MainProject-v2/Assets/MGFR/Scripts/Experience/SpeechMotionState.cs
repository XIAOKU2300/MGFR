using UnityEngine;

namespace MGFR.Experience
{
 public sealed class SpeechMotionState
 {
  public float Weight {get;private set;}
  public bool Active {get;private set;}
  float velocity;double lastAudible=-100;int round=-1;bool heard;
  static AnimationCurve Curve(params float[] values)
  {
   var keys=new Keyframe[values.Length/2];for(int i=0;i<keys.Length;i++)keys[i]=new Keyframe(values[i*2],values[i*2+1],0,0);
   return new AnimationCurve(keys);
  }
  static readonly AnimationCurve Left=Curve(0,0,.32f,.15f,.72f,.85f,1.13f,.48f,1.7f,0,2.48f,-.2f,3.1f,.3f,3.65f,.12f,4.6f,0);
  static readonly AnimationCurve Right=Curve(0,.12f,.55f,.04f,1.05f,.38f,1.68f,.7f,2.1f,.2f,2.85f,-.12f,3.55f,.4f,4.1f,.14f,4.6f,.12f);
  public void Tick(bool audible,bool pending,int currentRound,double now,float delta)
  {
   if(currentRound!=round){round=currentRound;heard=false;lastAudible=-100;}
   if(audible){heard=true;lastAudible=now;}
   Active=audible||(heard&&(pending||now-lastAudible<.28));
   Weight=Mathf.SmoothDamp(Weight,Active?1:0,ref velocity,Active?.16f:.28f,Mathf.Infinity,delta);
  }
  public static bool AffectsBone(int index)=>index==13||index==14||index==15||index==29||index==30||index==32||index==35||index==38||index==55||index==56||index==58||index==61||index==64;
  public static Quaternion BoneOffset(int index,float seconds)
  {
   float time=Mathf.Repeat(seconds,4.6f),left=Left.Evaluate(time),right=Right.Evaluate(time);
   float breath=Mathf.Sin(seconds*1.67f),turn=Mathf.Sin(seconds*.83f+.4f);
   switch(index)
   {
    case 13:return Quaternion.Euler(.65f*breath,1.3f*turn,.7f*(left-right));
    case 14:return Quaternion.Euler(.5f*breath,.65f*turn,.35f*(left-right));
    case 15:return Quaternion.Euler(.25f*breath,.4f*turn,0);
    case 29:case 30:return Quaternion.Euler(0,0,1.1f*left);
    case 32:return Quaternion.Euler(2.2f*left,-1.4f*left,5.5f*left);
    case 35:return Quaternion.Euler(5.5f*left,2.2f*left,0);
    case 38:return Quaternion.Euler(2.3f*left,-3.4f*left,2.5f*left);
    case 55:case 56:return Quaternion.Euler(0,0,-.9f*right);
    case 58:return Quaternion.Euler(1.7f*right,1.2f*right,-4.8f*right);
    case 61:return Quaternion.Euler(4.8f*right,-2.3f*right,0);
    case 64:return Quaternion.Euler(1.8f*right,3*right,-2.3f*right);
    default:return Quaternion.identity;
   }
  }
  public static Vector3 HeadOffset(float seconds)=>new Vector3(1.6f*Left.Evaluate(Mathf.Repeat(seconds,4.6f)),.8f*Mathf.Sin(seconds*.83f),.6f*Mathf.Sin(seconds*1.1f));
 }
}
