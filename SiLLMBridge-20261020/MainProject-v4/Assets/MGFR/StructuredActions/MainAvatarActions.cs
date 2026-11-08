using System;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Attention;
using MGFR.Skins;

namespace MGFR.StructuredActions {
 [Serializable] public class NativeNode {public string name;public int parent;public float[] t,q,s;}
 [Serializable] public class BoneMapping {public int source;public string target_name;}
 [Serializable] public class NativeRig {public NativeNode[] nodes;public BoneMapping[] mapping;}
 [Serializable] public class MotionInfo {public string name,file,label;public float duration,fps;public int frames;}
 [Serializable] public class MotionList {public MotionInfo[] clips;}
 [Serializable] public class ActionCue {public string name;public float at,duration;}
 [Serializable] public class SpeechPlan {public int sequence,voice_round=-1;public string turn_id,text,emotion,expression_variant;public float emotion_intensity=.65f,speech_duration=10;public ActionCue[] actions;}
 [Serializable] public class ShapeWeight {public string name;public float weight;}
 [Serializable] public class EmotionPose {public string name,emotion,label;public ShapeWeight[] weights;}
 [Serializable] public class EmotionPoses {public EmotionPose[] poses;}

 [DefaultExecutionOrder(810)]
 public sealed class MainAvatarActions:MonoBehaviour {
  public bool Ready {get;private set;} public string CurrentAction {get;private set;}="idle";
  public string CurrentEmotion=>plan!=null?plan.emotion:"neutral";public string CurrentExpression=>plan!=null?plan.expression_variant:"native";
  public float BodyWeight {get;private set;} public float EmotionWeight {get;private set;}
  public int MappedBones=>targets!=null?targets.Length:0;
  public bool ReviewSpeaking; public bool ReviewOverride;
  SiCharacterLoader loader;IdleMotionPlayer idle;DialogueClient voice;DialogueAudioOutput audio;FaceAttentionController attention;
  string root,json;volatile bool running;Thread poller;SpeechPlan plan;int seenSequence=-1;float planStart,lastAudible=-100;
  bool heard;float genericStart;NativeRig rig;MotionList motions;Quaternion[] sourceRest,sourceWorld,sourceLocal,targetRest,baseWorld,previousWorld;
  Transform[] targets;int[] sourceIndices;Dictionary<string,int> actionIndices=new Dictionary<string,int>();
  Dictionary<string,EmotionPose> expressions=new Dictionary<string,EmotionPose>();Dictionary<string,int> shapeIds=new Dictionary<string,int>();Dictionary<string,float> shapeValues=new Dictionary<string,float>();
  int active=-1,frames;float fps,phaseStart;float[] motion;float clipClock;float switchAt;Quaternion faceTurn=Quaternion.Euler(0,180,0);
  static readonly HashSet<string> AttentionShapes=new HashSet<string>{"にこり","困る","上","口角上げ","口角下げ","笑い","びっくり"};

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Install(){
   var args=Environment.GetCommandLineArgs();if(SceneManager.GetActiveScene().name!=SiCharacterBootstrap.SceneName||Array.IndexOf(args,"-mgfr-llm-actions")<0)return;
   new GameObject("MGFR structured speech actions").AddComponent<MainAvatarActions>();
  }
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-avatar-data");root=at>=0&&at+1<args.Length?args[at+1]:Path.Combine(Application.streamingAssetsPath,"avatar-actions");
   while((idle=FindAnyObjectByType<IdleMotionPlayer>())==null||(voice=FindAnyObjectByType<DialogueClient>())==null)yield return null;
   var skins=FindAnyObjectByType<SiSkinSwitcher>();while(skins!=null&&!skins.IsReady)yield return null;
   loader=skins!=null?skins.Loader:FindAnyObjectByType<SiCharacterLoader>();while(loader==null||!loader.IsReady)yield return null;
   yield return null;yield return null;
   try{Initialize();}catch(Exception e){Debug.LogError("[MGFR structured actions] startup failed "+e.GetType().Name);yield break;}
  }
  void Initialize(){
   audio=voice.GetComponent<DialogueAudioOutput>();attention=FindAnyObjectByType<FaceAttentionController>();
   rig=JsonUtility.FromJson<NativeRig>(File.ReadAllText(Path.Combine(root,"source-rig.json")));motions=JsonUtility.FromJson<MotionList>(File.ReadAllText(Path.Combine(root,"motions/manifest.json")));
   for(int i=0;i<motions.clips.Length;i++)actionIndices.Add(motions.clips[i].name,i);
   var p=JsonUtility.FromJson<EmotionPoses>(File.ReadAllText(Path.Combine(root,"expressions.json")));
   foreach(var pose in p.poses){expressions.Add(pose.name,pose);foreach(var w in pose.weights)if(!shapeIds.ContainsKey(w.name)){int id=loader.Renderer.sharedMesh.GetBlendShapeIndex(w.name);if(id<0)throw new Exception("Expression shape missing");shapeIds.Add(w.name,id);shapeValues.Add(w.name,0);}}
   sourceRest=new Quaternion[rig.nodes.Length];sourceWorld=new Quaternion[rig.nodes.Length];sourceLocal=new Quaternion[rig.nodes.Length];
   for(int i=0;i<rig.nodes.Length;i++){var n=rig.nodes[i];var q=new Quaternion(n.q[0],n.q[1],n.q[2],n.q[3]);sourceRest[i]=n.parent<0?q:sourceRest[n.parent]*q;}
   var bones=loader.Renderer.bones;var names=new Dictionary<string,Transform>();foreach(var b in bones)if(!names.ContainsKey(b.name))names.Add(b.name,b);
   targets=new Transform[rig.mapping.Length];sourceIndices=new int[targets.Length];targetRest=new Quaternion[targets.Length];baseWorld=new Quaternion[targets.Length];previousWorld=new Quaternion[targets.Length];
   var saved=new Quaternion[bones.Length];for(int i=0;i<bones.Length;i++){saved[i]=bones[i].localRotation;bones[i].localRotation=Quaternion.identity;}
   for(int i=0;i<targets.Length;i++){targets[i]=names[rig.mapping[i].target_name];sourceIndices[i]=rig.mapping[i].source;targetRest[i]=Quaternion.Inverse(loader.transform.rotation)*targets[i].rotation;}
   for(int i=0;i<bones.Length;i++)bones[i].localRotation=saved[i];
   // Keep natural idle, footwear, gaze, lip sync and secondary physics. Disable
   // the old component's automatic speech-curve writer, then sample only its
   // zero-speech idle base before layering the authored native clips.
   idle.enabled=false;Load(actionIndices["idle"]);Ready=true;running=true;poller=new Thread(Poll){IsBackground=true,Name="MGFR avatar plan"};poller.Start();
   gameObject.AddComponent<MainEmotionLate>().Driver=this;
   Debug.Log("MGFR_MAIN_ACTIONS_READY clips="+motions.clips.Length+" variants="+expressions.Count+" sourceBones="+rig.nodes.Length+" targetBones="+bones.Length+" mapped="+targets.Length+" legacySpeechCurves=False");
  }
  void Poll(){while(running){try{var req=(HttpWebRequest)WebRequest.Create("http://127.0.0.1:18766/v1/player/plan");req.Proxy=null;req.Timeout=1500;req.ReadWriteTimeout=1500;req.KeepAlive=false;
   using(var response=req.GetResponse())using(var reader=new StreamReader(response.GetResponseStream(),Encoding.UTF8))Interlocked.Exchange(ref json,reader.ReadToEnd());
  }catch(WebException){}catch(IOException){} if(running)Thread.Sleep(120);}}
  void Load(int index){if(active==index)return;
   using(var r=new BinaryReader(File.OpenRead(Path.Combine(root,"motions",motions.clips[index].file)))){
    if(Encoding.ASCII.GetString(r.ReadBytes(8))!="ENFMOT1\0"||r.ReadInt32()!=rig.nodes.Length)throw new Exception("Native motion contract");frames=r.ReadInt32();fps=r.ReadSingle();var bytes=r.ReadBytes(checked(frames*rig.nodes.Length*40));if(bytes.Length!=frames*rig.nodes.Length*40)throw new Exception("Truncated motion");motion=new float[bytes.Length/4];Buffer.BlockCopy(bytes,0,motion,0,bytes.Length);
   }active=index;switchAt=Time.unscaledTime;CurrentAction=motions.clips[index].name;
  }
  public void SetReviewPlan(SpeechPlan p){plan=p;seenSequence=p.sequence;planStart=Time.unscaledTime;genericStart=planStart;heard=false;}
  void LateUpdate(){if(!Ready)return;
   string value=Interlocked.Exchange(ref json,null);if(value!=null&&!ReviewOverride){try{var incoming=JsonUtility.FromJson<SpeechPlan>(value);if(incoming!=null&&incoming.sequence!=seenSequence){plan=incoming;seenSequence=incoming.sequence;heard=false;planStart=-1;genericStart=Time.unscaledTime;Debug.Log("MGFR_MAIN_PLAN sequence="+seenSequence+" emotion="+incoming.emotion+" variant="+incoming.expression_variant);}}catch(Exception){}}
   bool audible=ReviewOverride?ReviewSpeaking:voice.IsSpeaking;
   bool matches=plan!=null&&(plan.voice_round<0||plan.voice_round==voice.CurrentRound);
   bool generic=matches&&plan.voice_round<0&&Time.unscaledTime-genericStart<plan.speech_duration;
   if(matches&&(audible||generic)){if(!heard){heard=true;planStart=Time.unscaledTime;Debug.Log("MGFR_MAIN_PLAY sequence="+seenSequence+" actualAudio="+audible+" emotion="+plan.emotion+" variant="+plan.expression_variant);}lastAudible=Time.unscaledTime;}
   bool pending=audio!=null&&audio.PlaybackPending;
   bool playing=matches&&heard&&(audible||generic||(plan.voice_round>=0&&(pending||Time.unscaledTime-lastAudible<.28f)));
   if(!matches)heard=false;
   float dt=Mathf.Min(Time.unscaledDeltaTime,.05f);BodyWeight=Mathf.MoveTowards(BodyWeight,playing?1:0,dt/(playing?.28f:.4f));
   EmotionWeight=Mathf.MoveTowards(EmotionWeight,playing&&plan.expression_variant!="native"?Mathf.Clamp01(plan.emotion_intensity):0,dt/.45f);
   for(int i=0;i<targets.Length;i++)previousWorld[i]=targets[i].rotation;
   idle.Apply(Time.time,Time.unscaledDeltaTime); // Natural idle keeps advancing; legacy speech curves stay at zero.
   for(int i=0;i<targets.Length;i++)baseWorld[i]=targets[i].rotation;
   string selected="idle";float seconds=Time.unscaledTime;
   if(playing&&plan.actions!=null){float elapsed=Time.unscaledTime-planStart;foreach(var cue in plan.actions)if(cue.at<=elapsed&&elapsed<cue.at+cue.duration){selected=cue.name;seconds=elapsed-cue.at;break;}}
   if(!actionIndices.TryGetValue(selected,out int clip))clip=actionIndices["idle"];Load(clip);
   float duration=motions.clips[active].duration;seconds=selected=="idle"?Mathf.Repeat(seconds,duration):Mathf.Clamp(seconds,0,duration);clipClock=seconds;
   float frame=seconds*fps;int a=Mathf.Min((int)frame,frames-1),b=Mathf.Min(a+1,frames-1);float t=frame-a;
   for(int i=0;i<rig.nodes.Length;i++){int x=(a*rig.nodes.Length+i)*10,y=(b*rig.nodes.Length+i)*10;sourceLocal[i]=Quaternion.Slerp(new Quaternion(motion[x],motion[x+1],motion[x+2],motion[x+3]),new Quaternion(motion[y],motion[y+1],motion[y+2],motion[y+3]),t);sourceWorld[i]=rig.nodes[i].parent<0?sourceLocal[i]:sourceWorld[rig.nodes[i].parent]*sourceLocal[i];}
   var leg=FindAnyObjectByType<LegPlantSolver>();if(leg!=null)leg.enabled=!(selected.StartsWith("walk")&&BodyWeight>.01f);
   float transition=Mathf.SmoothStep(0,1,Mathf.Clamp01((Time.unscaledTime-switchAt)/.25f));
   for(int i=0;i<targets.Length;i++){
    string n=targets[i].name;bool head=n=="頭"||n=="首";bool lower=n=="下半身"||n.Contains("足")||n.Contains("ひざ")||n.Contains("つま先");
    // Chat gestures use the upper body; the established leg-planting and room
    // anchor remain responsible for feet. Native locomotion is previewed in place.
    if(head||(lower&&!selected.StartsWith("walk")))continue;int s=sourceIndices[i];var delta=faceTurn*(sourceWorld[s]*Quaternion.Inverse(sourceRest[s]))*Quaternion.Inverse(faceTurn);
    var desired=loader.transform.rotation*delta*targetRest[i];var blended=Quaternion.Slerp(baseWorld[i],desired,BodyWeight);
    targets[i].rotation=Quaternion.Slerp(previousWorld[i],blended,transition);
   }
   if(attention!=null&&BodyWeight>.01f){int h=Array.FindIndex(rig.nodes,n=>n.name=="Bip001_Head");var rest=new Quaternion(rig.nodes[h].q[0],rig.nodes[h].q[1],rig.nodes[h].q[2],rig.nodes[h].q[3]);var q=faceTurn*(sourceLocal[h]*Quaternion.Inverse(rest))*Quaternion.Inverse(faceTurn);var e=q.eulerAngles;attention.SubmitHeadGesture(new Vector3(Mathf.DeltaAngle(0,e.x),Mathf.DeltaAngle(0,e.y),Mathf.DeltaAngle(0,e.z))*BodyWeight,Time.unscaledTime);}
  }
  public void ApplyEmotion(){if(!Ready)return;
   EmotionPose pose=null;if(plan!=null)expressions.TryGetValue(plan.expression_variant??"",out pose);
   var desired=new Dictionary<string,float>();if(pose!=null)foreach(var w in pose.weights)desired[w.name]=w.weight;
   var controller=loader.GetComponent<SiCharacterController>();float mouth=controller!=null?controller.MouthOpen:0;
   float blink=loader.Renderer.GetBlendShapeWeight(loader.Renderer.sharedMesh.GetBlendShapeIndex("まばたき"))/100;
   foreach(var entry in shapeIds){float target=desired.TryGetValue(entry.Key,out float w)?w:0;float value=Mathf.Lerp(shapeValues[entry.Key],target,1-Mathf.Exp(-Time.unscaledDeltaTime*7));shapeValues[entry.Key]=value;
    float baseValue=AttentionShapes.Contains(entry.Key)?loader.Renderer.GetBlendShapeWeight(entry.Value):0;
    bool mouthShape=entry.Key.StartsWith("口")||entry.Key=="にっこり"||entry.Key=="にやり"||entry.Key=="∧"||entry.Key=="ω";
    float amount=EmotionWeight*(mouthShape?1-.85f*mouth:1);if(entry.Key=="笑い"||entry.Key=="びっくり"||entry.Key=="なごみ"||entry.Key=="じと目")amount*=1-Mathf.Clamp01(blink);
    loader.Renderer.SetBlendShapeWeight(entry.Value,Mathf.Clamp(Mathf.Lerp(baseValue,value*100,amount),0,100));
   }
  }
  void OnDestroy(){running=false;if(poller!=null)poller.Join(1800);if(idle!=null)idle.enabled=true;}
 }
 [DefaultExecutionOrder(1340)] public sealed class MainEmotionLate:MonoBehaviour {public MainAvatarActions Driver;void LateUpdate(){Driver?.ApplyEmotion();}}
}
