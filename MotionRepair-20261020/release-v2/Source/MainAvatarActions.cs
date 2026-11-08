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

namespace MGFR.StructuredVoiceFinal {
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
  int bridgePort=18766;
  string root,json;volatile bool running;Thread poller;SpeechPlan plan;int seenSequence=-1;float planStart,lastAudible=-100;
  bool heard;float genericStart;NativeRig rig;MotionList motions;Quaternion[] sourceRest,sourceWorld,sourceLocal,targetRest,baseWorld,previousWorld;
  Transform[] targets;int[] sourceIndices;Dictionary<string,int> actionIndices=new Dictionary<string,int>();
  Dictionary<string,EmotionPose> expressions=new Dictionary<string,EmotionPose>();Dictionary<string,int> shapeIds=new Dictionary<string,int>();Dictionary<string,float> shapeValues=new Dictionary<string,float>();
  int active=-1,frames;float fps,phaseStart;float[] motion;float clipClock;float switchAt;Quaternion faceTurn=Quaternion.Euler(0,180,0);
  Vector3[] sourcePosition,sourceScale;
  ArmBinding[] arms; Transform torsoLow,torsoHigh;float torsoRadiusX,torsoRadiusZ;
  public float ReviewClock=-1;public float MinArmClearance {get;private set;}=1;public int GuardCorrections {get;private set;}
  sealed class ArmBinding {public Transform upper,elbow,wrist;public int sourceUpper,sourceElbow,sourceWrist,upperMap,wristMap;public float a,b;public Vector3 smoothHint,smoothWrist,hintVelocity,wristVelocity;public Quaternion palm;public bool initialized;}
  static readonly HashSet<string> ReviewedActions=new HashSet<string>{"base_idle","tsundere","wave","idle","nod","shake_head","scratch_head","receive_gift","relaxed_idle","idle_special_2","arms_crossed","ponder","point","surprised_pose","talk_hands","introduce","scratch_head_start","think","settle"};
  public bool IsReviewedAction(string name){return ReviewedActions.Contains(name);}
  static bool IsArm(string name){return name=="左腕"||name=="右腕"||name=="左ひじ"||name=="右ひじ"||name=="左手首"||name=="右手首";}
  static readonly HashSet<string> AttentionShapes=new HashSet<string>{"にこり","困る","上","口角上げ","口角下げ","笑い","びっくり"};

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] public static void Install(){
   var args=Environment.GetCommandLineArgs();if(SceneManager.GetActiveScene().name!=SiCharacterBootstrap.SceneName||Array.IndexOf(args,"-mgfr-structured-voice")<0)return;
   if(FindAnyObjectByType<MainAvatarActions>()!=null)return;
   new GameObject("MGFR structured speech actions").AddComponent<MainAvatarActions>();
   if(Array.IndexOf(args,"-mgfr-catalog-review")>=0)new GameObject("Catalog continuity review").AddComponent<MotionCatalogReview>();
   if(Array.IndexOf(args,"-mgfr-motion-review")>=0)new GameObject("Motion continuity review").AddComponent<MotionContinuityReview>();
   if(Array.IndexOf(args,"-mgfr-actions-review")>=0)new GameObject("Main action acceptance").AddComponent<MainActionsReview>();
   if(Array.IndexOf(args,"-mgfr-actions-network-review")>=0)new GameObject("Main network acceptance").AddComponent<MainNetworkReview>();
  }
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-avatar-data");root=at>=0&&at+1<args.Length?args[at+1]:Path.Combine(Application.streamingAssetsPath,"avatar-actions");
   while((idle=FindAnyObjectByType<IdleMotionPlayer>())==null||(voice=FindAnyObjectByType<DialogueClient>())==null)yield return null;
   var skins=FindAnyObjectByType<SiSkinSwitcher>();while(skins!=null&&!skins.IsReady)yield return null;
   loader=skins!=null?skins.Loader:FindAnyObjectByType<SiCharacterLoader>();while(loader==null||!loader.IsReady)yield return null;
   yield return null;yield return null;
   try{Initialize();}catch(Exception e){Debug.LogException(e);Debug.LogError("[MGFR structured actions] startup failed "+e.GetType().Name);yield break;}
  }
  void Initialize(){
   var cmd=Environment.GetCommandLineArgs();int portAt=Array.IndexOf(cmd,"-mgfr-action-port");if(portAt>=0&&portAt+1<cmd.Length)bridgePort=int.Parse(cmd[portAt+1]);
   Debug.Log("MAIN_INIT_STAGE audio");audio=voice.GetComponent<DialogueAudioOutput>();attention=FindAnyObjectByType<FaceAttentionController>();
   Debug.Log("MAIN_INIT_STAGE rig");rig=JsonUtility.FromJson<NativeRig>(File.ReadAllText(Path.Combine(root,"source-rig.json")));motions=JsonUtility.FromJson<MotionList>(File.ReadAllText(Path.Combine(root,"motions/manifest.json")));
   for(int i=0;i<motions.clips.Length;i++)actionIndices.Add(motions.clips[i].name,i);
   Debug.Log("MAIN_INIT_STAGE faces");var p=JsonUtility.FromJson<EmotionPoses>(File.ReadAllText(Path.Combine(root,"expressions.json")));
   foreach(var pose in p.poses){expressions.Add(pose.name,pose);foreach(var w in pose.weights)if(!shapeIds.ContainsKey(w.name)){int id=loader.Renderer.sharedMesh.GetBlendShapeIndex(w.name);if(id<0)throw new Exception("Expression shape missing");shapeIds.Add(w.name,id);shapeValues.Add(w.name,0);}}
   Debug.Log("MAIN_INIT_STAGE rest");sourceRest=new Quaternion[rig.nodes.Length];sourceWorld=new Quaternion[rig.nodes.Length];sourceLocal=new Quaternion[rig.nodes.Length];
   for(int i=0;i<rig.nodes.Length;i++){var n=rig.nodes[i];var q=new Quaternion(n.q[0],n.q[1],n.q[2],n.q[3]);sourceRest[i]=n.parent<0?q:sourceRest[n.parent]*q;}
   Debug.Log("MAIN_INIT_STAGE target");var bones=loader.Renderer.bones;var names=new Dictionary<string,Transform>();foreach(var b in bones)if(!names.ContainsKey(b.name))names.Add(b.name,b);
   targets=new Transform[rig.mapping.Length];sourceIndices=new int[targets.Length];targetRest=new Quaternion[targets.Length];baseWorld=new Quaternion[targets.Length];previousWorld=new Quaternion[targets.Length];
   var saved=new Quaternion[bones.Length];for(int i=0;i<bones.Length;i++){saved[i]=bones[i].localRotation;bones[i].localRotation=Quaternion.identity;}
   for(int i=0;i<targets.Length;i++){targets[i]=names[rig.mapping[i].target_name];sourceIndices[i]=rig.mapping[i].source;targetRest[i]=Quaternion.Inverse(loader.transform.rotation)*targets[i].rotation;}
   for(int i=0;i<bones.Length;i++)bones[i].localRotation=saved[i];
   // Keep natural idle, footwear, gaze, lip sync and secondary physics. Disable
   // the old component's automatic speech-curve writer, then sample only its
   // zero-speech idle base before layering the authored native clips.
   sourcePosition=new Vector3[rig.nodes.Length];sourceScale=new Vector3[rig.nodes.Length];
   torsoLow=names["下半身"];torsoHigh=names["上半身2"];arms=new ArmBinding[2];
   for(int side=0;side<2;side++){
    string prefix=side==0?"左":"右",native=side==0?"Bip001_L_":"Bip001_R_";
    var arm=new ArmBinding{upper=names[prefix+"腕"],elbow=names[prefix+"ひじ"],wrist=names[prefix+"手首"]};
    arm.sourceUpper=Array.FindIndex(rig.nodes,n=>n.name==native+"UpperArm");arm.sourceElbow=Array.FindIndex(rig.nodes,n=>n.name==native+"Forearm");arm.sourceWrist=Array.FindIndex(rig.nodes,n=>n.name==native+"Hand");
    arm.upperMap=Array.FindIndex(targets,b=>b==arm.upper);arm.wristMap=Array.FindIndex(targets,b=>b==arm.wrist);
    arm.a=Vector3.Distance(arm.upper.position,arm.elbow.position);arm.b=Vector3.Distance(arm.elbow.position,arm.wrist.position);arms[side]=arm;
   }
   float shoulderWidth=Vector3.Distance(loader.transform.InverseTransformPoint(arms[0].upper.position),loader.transform.InverseTransformPoint(arms[1].upper.position));
   torsoRadiusX=shoulderWidth*.46f+.025f;torsoRadiusZ=shoulderWidth*.43f+.035f;
   Debug.Log("MGFR_LATEST_REPAIR body=direction-ik-guard speech=actual-audio arms="+arms.Length+" torsoX="+torsoRadiusX+" torsoZ="+torsoRadiusZ+" listenerVolume="+AudioListener.volume+" outputRate="+AudioSettings.outputSampleRate);
   Debug.Log("MAIN_INIT_STAGE activate");idle.enabled=false;finalPose=new Quaternion[targets.Length];transitionPose=new Quaternion[targets.Length];foreach(var item in actionIndices)if(ReviewedActions.Contains(item.Key))CacheClip(item.Value);Load(actionIndices["idle"]);Ready=true;running=true;poller=new Thread(Poll){IsBackground=true,Name="MGFR avatar plan"};poller.Start();
   gameObject.AddComponent<MainEmotionLate>().Driver=this;
   Debug.Log("MGFR_MAIN_ACTIONS_READY clips="+motions.clips.Length+" variants="+expressions.Count+" sourceBones="+rig.nodes.Length+" targetBones="+bones.Length+" mapped="+targets.Length+" legacySpeechCurves=False");
  }
  void Poll(){int failures=0;while(running){try{
   using(var tcp=new System.Net.Sockets.TcpClient()){
    tcp.Connect("127.0.0.1",bridgePort);using(var stream=tcp.GetStream()){
     stream.ReadTimeout=1500;stream.WriteTimeout=1500;byte[] request=Encoding.ASCII.GetBytes("GET /v1/player/plan HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n");stream.Write(request,0,request.Length);
     using(var reader=new StreamReader(stream,Encoding.UTF8)){string response=reader.ReadToEnd();int split=response.IndexOf("\r\n\r\n",StringComparison.Ordinal);if(split>=0&&response.StartsWith("HTTP/1.0 200",StringComparison.Ordinal))Interlocked.Exchange(ref json,response.Substring(split+4));else if(failures++<2)Debug.LogWarning("MGFR plan HTTP response rejected");}
    }
   }
  }catch(System.Net.Sockets.SocketException){if(failures++<2)Debug.LogWarning("MGFR plan bridge not connected yet");}catch(IOException){if(failures++<2)Debug.LogWarning("MGFR plan read timed out");} if(running)Thread.Sleep(120);}}

  sealed class CachedClip {public int frames;public float fps;public float[] values;}
  readonly Dictionary<int,CachedClip> cached=new Dictionary<int,CachedClip>();
  Quaternion[] finalPose,transitionPose; bool poseReady;string cueKey="";
  float blendStarted,actionStarted;int heldClip=-1;string heldKey="";
  Vector3 headOffset,headVelocity;Quaternion[] baseLocal;
  float sampleNow;public float ReviewDelta=1f/60f;
  public bool ReviewManual;public int ClipReads {get;private set;}
  public float MotionClock=>clipClock;
  public void StepReview(float now,float delta){ReviewClock=now;ReviewDelta=delta;LateUpdate();}
  void CacheClip(int index){
   if(cached.ContainsKey(index))return;
   using(var reader=new BinaryReader(File.OpenRead(Path.Combine(root,"motions",motions.clips[index].file)))){
    if(Encoding.ASCII.GetString(reader.ReadBytes(8))!="ENFMOT1\0"||reader.ReadInt32()!=rig.nodes.Length)throw new InvalidDataException("Motion skeleton contract");
    int count=reader.ReadInt32();float rate=reader.ReadSingle();
    if(count<2||rate<=0||rate>240)throw new InvalidDataException("Motion sampling contract");
    var bytes=reader.ReadBytes(checked(count*rig.nodes.Length*40));
    if(bytes.Length!=count*rig.nodes.Length*40)throw new InvalidDataException("Truncated motion");
    var values=new float[bytes.Length/4];Buffer.BlockCopy(bytes,0,values,0,bytes.Length);
    cached.Add(index,new CachedClip{frames=count,fps=rate,values=values});ClipReads++;
   }
  }
  void Load(int index){
   if(active==index)return;
   if(!cached.TryGetValue(index,out var data))throw new InvalidOperationException("Clip was not preloaded");
   active=index;frames=data.frames;fps=data.fps;motion=data.values;CurrentAction=motions.clips[index].name;
  }
  public void SetReviewPlan(SpeechPlan p){plan=p;seenSequence=p.sequence;planStart=ReviewClock>=0?ReviewClock:Time.unscaledTime;genericStart=planStart;heard=false;heldClip=-1;heldKey="";}
  void LateUpdate(){
   if(!Ready||ReviewManual&&ReviewClock<0)return;
   float now=ReviewClock>=0?ReviewClock:Time.unscaledTime;
   float dt=Mathf.Clamp(ReviewClock>=0?ReviewDelta:Time.unscaledDeltaTime,.0001f,.05f);sampleNow=now;
   string value=Interlocked.Exchange(ref json,null);
   if(value!=null&&!ReviewOverride){try{
    var incoming=JsonUtility.FromJson<SpeechPlan>(value);
    if(incoming!=null&&incoming.sequence!=seenSequence){plan=incoming;seenSequence=incoming.sequence;heard=false;planStart=-1;genericStart=now;heldClip=-1;}
   }catch(Exception e){Debug.LogWarning("MGFR plan rejected: "+e.GetType().Name);}}
   bool audible=ReviewOverride?ReviewSpeaking:voice.IsSpeaking;
   bool matches=plan!=null&&(plan.voice_round<0||plan.voice_round==voice.CurrentRound);
   bool generic=matches&&plan.voice_round<0&&now-genericStart<plan.speech_duration;
   if(matches&&(audible||generic)){if(!heard){heard=true;planStart=now;}lastAudible=now;}
   bool pending=audio!=null&&audio.PlaybackPending;
   bool playing=matches&&heard&&(audible||generic||(plan.voice_round>=0&&(pending||now-lastAudible<.28f)));
   if(!matches){heard=false;heldClip=-1;}
   // The old idle owns its own continuous base. It never receives final IK output.
   idle.Apply(now,dt);
   for(int i=0;i<targets.Length;i++)baseWorld[i]=targets[i].rotation;
   if(baseLocal==null)baseLocal=new Quaternion[targets.Length];for(int i=0;i<targets.Length;i++)baseLocal[i]=targets[i].localRotation;
   string selected="idle",nextKey="idle";float seconds=0;int chosen=-1;
   float elapsed=heard?Mathf.Max(0,now-planStart):0;
   if(playing&&plan.actions!=null)for(int i=0;i<plan.actions.Length;i++){
    var cue=plan.actions[i];if(cue==null||!ReviewedActions.Contains(cue.name)||cue.name=="idle"||!actionIndices.TryGetValue(cue.name,out int index))continue;
    float length=Mathf.Min(cue.duration,motions.clips[index].duration);
    if(cue.at<=elapsed&&elapsed<cue.at+length){chosen=index;nextKey=seenSequence+":"+i;seconds=elapsed-cue.at;break;}
   }
   if(chosen>=0){
    if(heldKey!=nextKey){heldKey=nextKey;heldClip=chosen;actionStarted=now-seconds;}
   }else if(heldClip>=0&&matches&&heard&&now-actionStarted<motions.clips[heldClip].duration){
    // Finish a started authored gesture across sentence gaps and normal audio end.
    chosen=heldClip;nextKey=heldKey;seconds=now-actionStarted;
   }else heldClip=-1;
   if(chosen>=0)selected=motions.clips[chosen].name;
   BodyWeight=Mathf.MoveTowards(BodyWeight,chosen>=0?1:0,dt/.4f);
   EmotionWeight=Mathf.MoveTowards(EmotionWeight,playing&&plan.expression_variant!="native"?Mathf.Clamp01(plan.emotion_intensity):0,dt/.45f);
   if(nextKey!=cueKey){
    cueKey=nextKey;blendStarted=now;
    for(int i=0;i<targets.Length;i++)transitionPose[i]=poseReady?finalPose[i]:baseLocal[i];
   }
   Load(chosen>=0?chosen:actionIndices["idle"]);clipClock=seconds;
   if(chosen>=0){
    float frame=Mathf.Clamp(seconds*fps,0,frames-1);int a=(int)frame,b=Mathf.Min(a+1,frames-1);float t=frame-a;
    for(int i=0;i<rig.nodes.Length;i++){
     int x=(a*rig.nodes.Length+i)*10,y=(b*rig.nodes.Length+i)*10;
     sourceLocal[i]=Quaternion.Slerp(new Quaternion(motion[x],motion[x+1],motion[x+2],motion[x+3]),new Quaternion(motion[y],motion[y+1],motion[y+2],motion[y+3]),t);
     int parent=rig.nodes[i].parent;sourceWorld[i]=parent<0?sourceLocal[i]:sourceWorld[parent]*sourceLocal[i];
     var pos=Vector3.Lerp(new Vector3(motion[x+4],motion[x+5],motion[x+6]),new Vector3(motion[y+4],motion[y+5],motion[y+6]),t);
     var scale=Vector3.Lerp(new Vector3(motion[x+7],motion[x+8],motion[x+9]),new Vector3(motion[y+7],motion[y+8],motion[y+9]),t);
     sourcePosition[i]=parent<0?pos:sourcePosition[parent]+sourceWorld[parent]*Vector3.Scale(sourceScale[parent],pos);
     sourceScale[i]=parent<0?scale:Vector3.Scale(sourceScale[parent],scale);
    }
    for(int i=0;i<targets.Length;i++){
     string n=targets[i].name;if(n=="頭"||n=="首"||IsArm(n)||IsLower(n))continue;
     int s=sourceIndices[i];var delta=faceTurn*(sourceWorld[s]*Quaternion.Inverse(sourceRest[s]))*Quaternion.Inverse(faceTurn);
     targets[i].rotation=loader.transform.rotation*delta*targetRest[i];
    }
    // Solve the full target first. Fading the IK input made the collision guard snap on.
    // Arms are solved after the continuous torso pose, in constrained position space.
   }
   float fade=Mathf.SmoothStep(0,1,Mathf.Clamp01((now-blendStarted)/.48f));
   for(int i=0;i<targets.Length;i++){
    string n=targets[i].name;if(n=="頭"||n=="首"||IsArm(n)||IsLower(n))continue;
    var target=Quaternion.Slerp(transitionPose[i],targets[i].localRotation,fade);
    if(poseReady){
     var smooth=Quaternion.Slerp(finalPose[i],target,1-Mathf.Exp(-dt/.045f));
     target=Quaternion.RotateTowards(finalPose[i],smooth,(IsArm(n)?240f:140f)*dt);
    }
    targets[i].localRotation=finalPose[i]=target;
   }
   foreach(var arm in arms)ApplyNativeArm(arm,chosen>=0?1:0,dt);
   poseReady=true;MinArmClearance=ArmClearance();
   Vector3 desiredHead=Vector3.zero;
   if(chosen>=0){int h=Array.FindIndex(rig.nodes,n=>n.name=="Bip001_Head");
    var rest=new Quaternion(rig.nodes[h].q[0],rig.nodes[h].q[1],rig.nodes[h].q[2],rig.nodes[h].q[3]);var q=faceTurn*(sourceLocal[h]*Quaternion.Inverse(rest))*Quaternion.Inverse(faceTurn);var e=q.eulerAngles;
    desiredHead=new Vector3(Mathf.Clamp(Mathf.DeltaAngle(0,e.x),-12,12),Mathf.Clamp(Mathf.DeltaAngle(0,e.y),-12,12),Mathf.Clamp(Mathf.DeltaAngle(0,e.z),-8,8))*fade;
   }
   headOffset=Vector3.SmoothDamp(headOffset,desiredHead,ref headVelocity,.14f,80f,dt);
   if(attention!=null&&(chosen>=0||headOffset.sqrMagnitude>.0001f))attention.SubmitHeadGesture(headOffset,Time.unscaledTime);

  }
  static bool IsLower(string n)=>n=="下半身"||n.Contains("足")||n.Contains("ひざ")||n.Contains("つま先");
  public void ReviewAt(float seconds){ReviewClock=seconds;BodyWeight=1;LateUpdate();}
  Vector3 TorsoCenter(float y){
   var lo=loader.transform.InverseTransformPoint(torsoLow.position);var hi=loader.transform.InverseTransformPoint(torsoHigh.position);
   float k=Mathf.InverseLerp(lo.y,hi.y,y);return Vector3.Lerp(lo,hi,k);
  }
  float Clearance(Vector3 world,float padding){
   var p=loader.transform.InverseTransformPoint(world);var lo=loader.transform.InverseTransformPoint(torsoLow.position);var hi=loader.transform.InverseTransformPoint(torsoHigh.position);
   if(p.y<lo.y-.12f||p.y>hi.y+.09f)return 1;
   var c=TorsoCenter(p.y);float x=(p.x-c.x)/(torsoRadiusX+padding),z=(p.z-c.z)/(torsoRadiusZ+padding);
   return Mathf.Sqrt(x*x+z*z)-1;
  }
  Vector3 OutsideTorso(Vector3 world,float padding){
   if(Clearance(world,padding)>=0)return world;
   var p=loader.transform.InverseTransformPoint(world);var c=TorsoCenter(p.y);
   float x=Mathf.Clamp((p.x-c.x)/(torsoRadiusX+padding),-.999f,.999f);
   p.z=c.z-(torsoRadiusZ+padding)*Mathf.Sqrt(1-x*x);GuardCorrections++;
   return loader.transform.TransformPoint(p);
  }
  void SolveArm(ArmBinding arm,Vector3 wrist,Vector3 hint,out Vector3 elbow,out Vector3 end){
   Vector3 start=arm.upper.position;Vector3 aim=wrist-start;float distance=Mathf.Clamp(aim.magnitude,Mathf.Abs(arm.a-arm.b)+.001f,arm.a+arm.b-.001f);Vector3 direction=aim.sqrMagnitude>.000001f?aim.normalized:Vector3.down;
   float along=(arm.a*arm.a-arm.b*arm.b+distance*distance)/(2*distance);float height=Mathf.Sqrt(Mathf.Max(0,arm.a*arm.a-along*along));
   Vector3 bend=Vector3.ProjectOnPlane(hint-start,direction);if(bend.sqrMagnitude<.000001f)bend=Vector3.ProjectOnPlane(loader.transform.forward*-1,direction);
   elbow=start+direction*along+bend.normalized*height;end=start+direction*distance;
  }
  void ApplyNativeArm(ArmBinding arm,float weight,float dt){
   Vector3 start=arm.upper.position;
   var upperBase=(arm.elbow.position-start).normalized;var foreBase=(arm.wrist.position-arm.elbow.position).normalized;
   var upperNative=(loader.transform.rotation*faceTurn*(sourcePosition[arm.sourceElbow]-sourcePosition[arm.sourceUpper])).normalized;
   var foreNative=(loader.transform.rotation*faceTurn*(sourcePosition[arm.sourceWrist]-sourcePosition[arm.sourceElbow])).normalized;
   var hint=start+Vector3.Slerp(upperBase,upperNative,weight)*arm.a;
   var wrist=hint+Vector3.Slerp(foreBase,foreNative,weight)*arm.b;
   hint=OutsideTorso(hint,.025f);wrist=OutsideTorso(wrist,.065f);
   var localHint=loader.transform.InverseTransformPoint(hint);var localWrist=loader.transform.InverseTransformPoint(wrist);
   if(!arm.initialized){arm.smoothHint=loader.transform.InverseTransformPoint(arm.elbow.position);arm.smoothWrist=loader.transform.InverseTransformPoint(arm.wrist.position);arm.palm=Quaternion.Inverse(loader.transform.rotation)*arm.wrist.rotation;arm.initialized=true;}
   arm.smoothHint=Vector3.SmoothDamp(arm.smoothHint,localHint,ref arm.hintVelocity,.16f,1.5f,dt);
   arm.smoothWrist=Vector3.SmoothDamp(arm.smoothWrist,localWrist,ref arm.wristVelocity,.16f,1.5f,dt);
   hint=OutsideTorso(loader.transform.TransformPoint(arm.smoothHint),.025f);
   wrist=OutsideTorso(loader.transform.TransformPoint(arm.smoothWrist),.065f);
   Vector3 elbow,end;SolveArm(arm,wrist,hint,out elbow,out end);
   for(int step=0;step<18;step++){
    float penetration=0;
    for(int sample=0;sample<=8;sample++)penetration=Mathf.Min(penetration,Clearance(Vector3.Lerp(elbow,end,sample/8f),.04f));
    if(penetration>=0&&Clearance(elbow,.025f)>=0)break;
    float correction=Mathf.Clamp(-penetration*(torsoRadiusZ+.04f)*1.8f,.0004f,.025f);
    var forward=loader.transform.TransformVector(Vector3.back)*correction;
    hint=OutsideTorso(elbow,.03f)+forward;wrist=OutsideTorso(end,.065f)+forward;
    SolveArm(arm,wrist,hint,out elbow,out end);
   }
   arm.smoothHint=loader.transform.InverseTransformPoint(elbow);arm.smoothWrist=loader.transform.InverseTransformPoint(end);
   arm.upper.rotation=Quaternion.FromToRotation(arm.elbow.position-start,elbow-start)*arm.upper.rotation;
   arm.elbow.rotation=Quaternion.FromToRotation(arm.wrist.position-arm.elbow.position,end-arm.elbow.position)*arm.elbow.rotation;
   var palm=Quaternion.Inverse(loader.transform.rotation)*baseWorld[arm.wristMap];
   arm.palm=Quaternion.Slerp(arm.palm,palm,1-Mathf.Exp(-dt/.1f));arm.wrist.rotation=loader.transform.rotation*arm.palm;
  }
  public float ArmClearance(){
   if(arms==null)return 1;float result=1;
   foreach(var arm in arms){result=Mathf.Min(result,Clearance(arm.wrist.position,.035f));for(int sample=1;sample<=5;sample++)result=Mathf.Min(result,Clearance(Vector3.Lerp(arm.elbow.position,arm.wrist.position,sample/5f),.018f));}
   return result;
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
