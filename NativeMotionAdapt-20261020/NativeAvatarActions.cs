using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Attention;
using MGFR.Skins;
using MGFR.Wardrobe;
namespace MGFR.StructuredVoiceFinal {
 [Serializable] public class MotionInfo {public string name,file,label;public float duration,fps;public int frames;public bool loop;}
 [Serializable] public class MotionList {public MotionInfo[] clips;}
 [Serializable] public class ActionCue {public string name;public float at,duration;}
 [Serializable] public class SpeechPlan {public int sequence,voice_round=-1;public string turn_id,text,emotion,expression_variant;public float emotion_intensity=.65f,speech_duration=10;public ActionCue[] actions;}
 [Serializable] public class ShapeWeight {public string name;public float weight;}
 [Serializable] public class EmotionPose {public string name,emotion,label;public ShapeWeight[] weights;}
 [Serializable] public class EmotionPoses {public EmotionPose[] poses;}
 [DefaultExecutionOrder(810)] public sealed class MainAvatarActions:MonoBehaviour {
  public bool Ready {get;private set;}public string CurrentAction {get;private set;}="idle";
  public string CurrentEmotion=>plan!=null?plan.emotion:"neutral";public string CurrentExpression=>plan!=null?plan.expression_variant:"native";
  public float BodyWeight {get;private set;}public float EmotionWeight {get;private set;}public int MappedBones {get;private set;}
  public bool ReviewOverride,ReviewSpeaking;public int ClipReads {get;private set;}public float MotionClock=>anim!=null&&stateName!=null?anim[stateName].time:0;
  SiCharacterLoader loader;SiSkinSwitcher skins;DialogueClient voice;DialogueAudioOutput audio;IdleMotionPlayer idle;FaceAttentionController attention;Animation anim;
  readonly Dictionary<string,EmotionPose> expressions=new Dictionary<string,EmotionPose>();readonly Dictionary<string,int> shapeIds=new Dictionary<string,int>();readonly Dictionary<string,float> shapeValues=new Dictionary<string,float>();
  readonly Dictionary<string,MotionInfo> clips=new Dictionary<string,MotionInfo>();
  static readonly HashSet<string> AttentionShapes=new HashSet<string>{"にこり","困る","上","口角上げ","口角下げ","笑い","びっくり"};
  string root,baked,json,skinId,stateName="",cueKey="idle",heldKey="";int sequence=-1,slot,port=18766;SpeechPlan plan;bool heard;float started,genericStart,lastAudible=-100,heldStarted;string heldAction;
  volatile bool running;Thread poller;Vector3 head,headVelocity;
  public bool IsReviewedAction(string name)=>clips.ContainsKey(name);
  public static void Install(){var args=Environment.GetCommandLineArgs();if(Array.IndexOf(args,"-mgfr-structured-voice")<0)return;if(FindAnyObjectByType<MainAvatarActions>()!=null)return;
   var go=new GameObject("Native retargeted avatar actions");go.AddComponent<MainAvatarActions>();
   if(Array.IndexOf(args,"-mgfr-native-review")>=0)new GameObject("Native acceptance").AddComponent<NativeAcceptance>();
   if(Array.IndexOf(args,"-mgfr-actions-network-review")>=0)new GameObject("Native network acceptance").AddComponent<MainNetworkReview>();
  }
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();root=Arg(args,"-mgfr-avatar-data",Path.Combine(Application.streamingAssetsPath,"avatar-actions"));baked=Arg(args,"-mgfr-native-data",Path.Combine(Application.streamingAssetsPath,"native-actions"));port=int.Parse(Arg(args,"-mgfr-action-port","18766"));
   while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||(voice=FindAnyObjectByType<DialogueClient>())==null)yield return null;
   loader=skins.Loader;idle=FindAnyObjectByType<IdleMotionPlayer>();while(idle==null){yield return null;idle=FindAnyObjectByType<IdleMotionPlayer>();}
   yield return null;yield return null;
   try{Initialize();}catch(Exception e){Debug.LogError("NATIVE_ACTION_INIT_FAILED "+e.GetType().Name);Debug.LogException(e);yield break;}
  }
  static string Arg(string[] args,string key,string fallback){int i=Array.IndexOf(args,key);return i>=0&&i+1<args.Length?args[i+1]:fallback;}
  void Initialize(){
   audio=voice.GetComponent<DialogueAudioOutput>();attention=FindAnyObjectByType<FaceAttentionController>();
   var manifest=JsonUtility.FromJson<MotionList>(File.ReadAllText(Path.Combine(root,"motions/manifest.json")));foreach(var c in manifest.clips)clips.Add(c.name,c);
   var poses=JsonUtility.FromJson<EmotionPoses>(File.ReadAllText(Path.Combine(root,"expressions.json")));foreach(var pose in poses.poses){expressions.Add(pose.name,pose);foreach(var w in pose.weights)if(!shapeIds.ContainsKey(w.name)){int id=loader.Renderer.sharedMesh.GetBlendShapeIndex(w.name);if(id<0)throw new Exception("Expression missing");shapeIds.Add(w.name,id);shapeValues.Add(w.name,0);}}
   idle.enabled=false;var leg=FindAnyObjectByType<LegPlantSolver>();if(leg!=null)leg.enabled=false;
   var bones=loader.Renderer.bones;for(int i=0;i<bones.Length;i++){bones[i].localRotation=Quaternion.identity;var p=loader.Data.bones[i].localScaled;bones[i].localPosition=new Vector3(p[0],p[1],p[2]);}
   anim=loader.gameObject.AddComponent<Animation>();anim.playAutomatically=false;anim.cullingType=AnimationCullingType.AlwaysAnimate;
   foreach(string skin in new[]{"swimsuit","original"})foreach(var c in manifest.clips)LoadClip(skin,c);
   skinId=skins.CurrentId;Switch("idle","idle",Time.unscaledTime%clips["idle"].duration,0);Ready=true;running=true;poller=new Thread(Poll){IsBackground=true,Name="Native action plans"};poller.Start();
   gameObject.AddComponent<NativeEmotionLate>().Driver=this;gameObject.AddComponent<NativeClothCoordinator>();
   Debug.Log("NATIVE_ACTIONS_READY clips="+clips.Count+" skinVariants=2 mapped="+MappedBones+" body=UnityAnimation legacyIK=False");
  }
  string BonePath(Transform b){string path=b.name;while(b.parent!=loader.transform){b=b.parent;if(b==null)throw new Exception("Bone hierarchy");path=b.name+"/"+path;}return path;}
  void LoadClip(string skin,MotionInfo info){using(var r=new BinaryReader(File.OpenRead(Path.Combine(baked,skin,info.name+".hpose")))){
   if(r.ReadInt32()!=0x45535048)throw new Exception("Baked motion format");int count=r.ReadInt32(),frames=r.ReadInt32();float fps=r.ReadSingle();if(frames!=info.frames||fps!=info.fps)throw new Exception("Clip sampling mismatch");MappedBones=count;var ids=new int[count];for(int i=0;i<count;i++)ids[i]=r.ReadInt32();
   var values=new float[count,7,frames];for(int f=0;f<frames;f++)for(int i=0;i<count;i++)for(int c=0;c<7;c++)values[i,c,f]=r.ReadSingle();
   var clip=new AnimationClip{legacy=true,frameRate=fps,wrapMode=info.name=="idle"?WrapMode.Loop:WrapMode.ClampForever};string[] property={"localPosition.x","localPosition.y","localPosition.z","localRotation.x","localRotation.y","localRotation.z","localRotation.w"};
   for(int i=0;i<count;i++){
    // Put quaternion samples in one hemisphere before computing curve tangents.
    for(int f=1;f<frames;f++){float dot=0;for(int c=3;c<7;c++)dot+=values[i,c,f]*values[i,c,f-1];if(dot<0)for(int c=3;c<7;c++)values[i,c,f]=-values[i,c,f];}
    string path=BonePath(loader.Renderer.bones[ids[i]]);
    for(int c=0;c<7;c++){bool constant=true;for(int f=1;f<frames;f++)if(Mathf.Abs(values[i,c,f]-values[i,c,0])>.000001f){constant=false;break;}
     var keys=new Keyframe[constant?2:frames];for(int k=0;k<keys.Length;k++){int f=constant?k*(frames-1):k;float tangent=constant?0:(values[i,c,Mathf.Min(f+1,frames-1)]-values[i,c,Mathf.Max(f-1,0)])*fps/(f==0||f==frames-1?1:2);keys[k]=new Keyframe(f/fps,values[i,c,f],tangent,tangent);}
     clip.SetCurve(path,typeof(Transform),property[c],new AnimationCurve(keys));
    }
   }
   clip.EnsureQuaternionContinuity();anim.AddClip(clip,skin+":"+info.name+":0");anim.AddClip(clip,skin+":"+info.name+":1");ClipReads++;
  }}
  void Switch(string name,string key,float seconds,float fade=.45f){slot=1-slot;string state=skinId+":"+name+":"+slot;anim[state].time=Mathf.Clamp(seconds,0,clips[name].duration);anim[state].speed=1;anim.CrossFade(state,fade,PlayMode.StopSameLayer);stateName=state;CurrentAction=name;cueKey=key;}
  void Update(){if(!Ready)return;
   // The shoe layer is additive. Remove last frame's lift before animation writes a fresh hip pose.
   if(ShoeFootPose.Instance!=null)ShoeFootPose.Instance.UndoLift();
   if(skins.CurrentId!=skinId){float time=MotionClock;skinId=skins.CurrentId;Switch(CurrentAction,cueKey,time,0);}
  }
  void Poll(){while(running){try{using(var tcp=new TcpClient()){
    tcp.Connect("127.0.0.1",port);using(var stream=tcp.GetStream()){stream.ReadTimeout=1500;stream.WriteTimeout=1500;var bytes=Encoding.ASCII.GetBytes("GET /v1/player/plan HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n");stream.Write(bytes,0,bytes.Length);using(var reader=new StreamReader(stream,Encoding.UTF8)){string response=reader.ReadToEnd();int split=response.IndexOf("\r\n\r\n",StringComparison.Ordinal);if(split>=0&&response.StartsWith("HTTP/1.0 200",StringComparison.Ordinal))Interlocked.Exchange(ref json,response.Substring(split+4));}}}
   }catch(SocketException){}catch(IOException){}if(running)Thread.Sleep(120);}}
  public void SetReviewPlan(SpeechPlan p){plan=p;sequence=p.sequence;heard=false;genericStart=Time.unscaledTime;heldAction=null;heldKey="";}
  void LateUpdate(){if(!Ready)return;float now=Time.unscaledTime,dt=Mathf.Min(Time.unscaledDeltaTime,.05f);string value=Interlocked.Exchange(ref json,null);
   if(value!=null&&!ReviewOverride){try{var incoming=JsonUtility.FromJson<SpeechPlan>(value);if(incoming!=null&&incoming.sequence!=sequence)SetReviewPlan(incoming);}catch(Exception){}}
   bool audible=ReviewOverride?ReviewSpeaking:voice.IsSpeaking;bool matches=plan!=null&&(plan.voice_round<0||plan.voice_round==voice.CurrentRound);
   bool generic=matches&&plan.voice_round<0&&now-genericStart<plan.speech_duration;
   if(matches&&(audible||generic)){if(!heard){heard=true;started=now;}lastAudible=now;}
   bool speaking=matches&&heard&&(audible||generic||(plan.voice_round>=0&&(audio.PlaybackPending||now-lastAudible<.28f)));
   if(!matches){heard=false;heldAction=null;}
   string action="idle",key="idle";float seconds=now%clips["idle"].duration;float elapsed=heard?now-started:0;
   if(speaking&&plan.actions!=null)for(int i=0;i<plan.actions.Length;i++){var c=plan.actions[i];if(c==null||c.name=="idle"||!clips.TryGetValue(c.name,out var info))continue;
    if(c.at<=elapsed&&elapsed<c.at+Mathf.Min(c.duration,info.duration)){action=c.name;key=sequence+":"+i;seconds=elapsed-c.at;if(heldKey!=key){heldAction=action;heldKey=key;heldStarted=now-seconds;}break;}}
   if(action=="idle"&&heldAction!=null&&matches&&heard&&now-heldStarted<clips[heldAction].duration){action=heldAction;key=heldKey;seconds=now-heldStarted;}else if(action=="idle")heldAction=null;
   if(key!=cueKey)Switch(action,key,seconds);
   BodyWeight=Mathf.MoveTowards(BodyWeight,action!="idle"?1:0,dt/.4f);EmotionWeight=Mathf.MoveTowards(EmotionWeight,speaking&&plan.expression_variant!="native"?Mathf.Clamp01(plan.emotion_intensity):0,dt/.45f);
   if(attention!=null){var bones=loader.Renderer.bones;var q=bones[16].localRotation*bones[17].localRotation;var e=q.eulerAngles;var target=new Vector3(Mathf.Clamp(Mathf.DeltaAngle(0,e.x),-12,12),Mathf.Clamp(Mathf.DeltaAngle(0,e.y),-12,12),Mathf.Clamp(Mathf.DeltaAngle(0,e.z),-8,8));head=Vector3.SmoothDamp(head,target,ref headVelocity,.12f,100,dt);attention.SubmitHeadGesture(head,now);}
  }
  public void ApplyEmotion(){if(!Ready)return;EmotionPose pose=null;if(plan!=null)expressions.TryGetValue(plan.expression_variant??"",out pose);var desired=new Dictionary<string,float>();if(pose!=null)foreach(var w in pose.weights)desired[w.name]=w.weight;
   var controller=loader.GetComponent<SiCharacterController>();float mouth=controller!=null?controller.MouthOpen:0;int blinkId=loader.Renderer.sharedMesh.GetBlendShapeIndex("まばたき");float blink=blinkId>=0?loader.Renderer.GetBlendShapeWeight(blinkId)/100:0;
   foreach(var entry in shapeIds){float target=desired.TryGetValue(entry.Key,out float w)?w:0;float v=Mathf.Lerp(shapeValues[entry.Key],target,1-Mathf.Exp(-Time.unscaledDeltaTime*7));shapeValues[entry.Key]=v;float baseline=AttentionShapes.Contains(entry.Key)?loader.Renderer.GetBlendShapeWeight(entry.Value):0;
    bool mouthShape=entry.Key.StartsWith("口")||entry.Key=="にっこり"||entry.Key=="にやり"||entry.Key=="∧"||entry.Key=="ω";float amount=EmotionWeight*(mouthShape?1-.85f*mouth:1);if(entry.Key=="笑い"||entry.Key=="びっくり"||entry.Key=="なごみ"||entry.Key=="じと目")amount*=1-Mathf.Clamp01(blink);loader.Renderer.SetBlendShapeWeight(entry.Value,Mathf.Clamp(Mathf.Lerp(baseline,v*100,amount),0,100));}
  }
  void OnDestroy(){running=false;if(poller!=null)poller.Join(1800);}
 }
 [DefaultExecutionOrder(1340)]public sealed class NativeEmotionLate:MonoBehaviour{public MainAvatarActions Driver;void LateUpdate(){Driver?.ApplyEmotion();}}
}
