using System.Collections.Generic;
using UnityEngine;
using MGFR.Attention;
using MGFR.SpeechMotion;
using MGFR.SpeechMotion.Natural;
using Joint=MGFR.SpeechMotion.Joint;

namespace MGFR.Experience
{
 // Text is queued at tts.start; only the audio read cursor can start its motion.
 // The old authored clips are reused, with one final writer in IdleMotionPlayer.
 public sealed class SpokenGestureState
 {
  struct Sentence {public int Round,Index;public string Text;public long Start;}
  readonly Queue<Sentence> queued=new Queue<Sentence>();
  readonly ConversationalGesturePlanner planner=new ConversationalGesturePlanner("Si live conversation");
  readonly MotionPose pose=new MotionPose();
  readonly bool[] committed=new bool[2];
  readonly Vector3[] smooth=new Vector3[(int)Joint.Count];
  NaturalSentencePlan plan;Sentence current;bool hasSentence;int round=-1;
  double lastBeat=-100;public int StartedSentences {get;private set;}
  public int StartedGestures {get;private set;}
  public float PeakDegrees {get;private set;}
  public Vector3 Head=>smooth[(int)Joint.Head];
  public void Queue(int turn,int index,string text,long cursor)
  {queued.Enqueue(new Sentence{Round=turn,Index=index,Text=text,Start=cursor});}
  public void Tick(int turn,long cursor,int rate,bool pending,bool audible,double now,float dt,FaceAttentionController face,string userText="")
  {
   if(turn!=round){round=turn;hasSentence=false;plan=null;if(turn==0)queued.Clear();}
   while(queued.Count>0&&queued.Peek().Round<turn)queued.Dequeue();
   while(queued.Count>0&&queued.Peek().Round==turn&&cursor>queued.Peek().Start)
   {
    current=queued.Dequeue();hasSentence=true;StartedSentences++;
    plan=planner.Plan(current.Text,current.Index,now);committed[0]=committed[1]=false;
    // A quiet, single explain beat for an otherwise still ordinary response.
    // Never a periodic wave; semantic cues retain their authored full amplitude.
    if(plan.Count==0&&current.Text.Length>=10&&now-lastBeat>7)
    {
     int variant=current.Index%3;var clip=NaturalGestureLibrary.Get(Gesture.OpenPalm,variant);
     plan=new NaturalSentencePlan(new[]{new NaturalGestureCue(Gesture.OpenPalm,variant,
      current.Index%2==1,.18,clip.Duration,.29,0,false)});lastBeat=now;
    }
    face?.BeginSpokenLine(current.Text,now);
    if(current.Index==0&&AttentionSpeechBridge.InputIsAffectionate(userText))face?.SetMood(FaceMood.Shy,now);
   }
   pose.Clear();
   if(hasSentence&&plan!=null&&(pending||audible))
   {
    double seconds=(cursor-current.Start)/(double)rate;
    for(int i=0;i<plan.Count;i++)
    {
     var cue=plan[i];double age=seconds-cue.Start;
     if(age<=0||age>=cue.Duration)continue;
     if(!committed[i]){planner.Commit(cue,now);committed[i]=true;StartedGestures++;}
     bool mirror=cue.Kind==Gesture.PointLeft||((cue.Kind==Gesture.Wave||cue.Kind==Gesture.OpenPalm)&&cue.LeftHand);
     NaturalGestureLibrary.Get(cue.Kind,cue.Variant).Add(age/cue.Duration,cue.Strength,mirror,pose);
    }
    NaturalGestureLibrary.Limit(pose);
   }
   float blend=1-Mathf.Exp(-18*Mathf.Min(dt,.04f));
   for(int i=0;i<smooth.Length;i++)
   {
    var a=pose[(Joint)i];var target=new Vector3((float)a.X,-(float)a.Y,-(float)a.Z);
    if(i==(int)Joint.LeftArm||i==(int)Joint.RightArm)
    {target.x=Mathf.Clamp(target.x,-28,32);target.y=Mathf.Clamp(target.y,-45,45);target.z=Mathf.Clamp(target.z,-60,60);}
    if(i==(int)Joint.LeftElbow||i==(int)Joint.RightElbow)target.x=Mathf.Clamp(target.x,0,112);
    smooth[i]=Vector3.Lerp(smooth[i],target,blend);PeakDegrees=Mathf.Max(PeakDegrees,smooth[i].magnitude);
   }
  }
  public Quaternion Offset(int bone,Quaternion basis)
  {
   Joint joint;
   switch(bone)
   {
    case 13:joint=Joint.Chest;break;
    case 32:joint=Joint.LeftArm;break;case 35:joint=Joint.LeftElbow;break;case 38:joint=Joint.LeftWrist;break;
    case 58:joint=Joint.RightArm;break;case 61:joint=Joint.RightElbow;break;case 64:joint=Joint.RightWrist;break;
    default:return Quaternion.identity;
   }
   return Quaternion.Inverse(basis)*Quaternion.Euler(smooth[(int)joint])*basis;
  }
 }
}
