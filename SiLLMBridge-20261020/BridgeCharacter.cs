using System;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using UnityEngine;

[Serializable] public class BridgeState {
 public int sequence; public string turn_id,cue_id,text,action,motion_file,emotion,expression;
 public float action_elapsed,action_duration,emotion_intensity,blend_seconds;
 public bool speaking,native_face_active,loop;
}
[Serializable] public class FacePoseEntry {public string name,file,emotion;}
[Serializable] public class FacePoseManifest {public int[] face_bones; public FacePoseEntry[] poses; public string neutral;}

public sealed class BridgeCharacter:MonoBehaviour {
 NativeMotionPlayer body; Camera view; string root,url="http://127.0.0.1:18766",latestJson;
 volatile bool running; Thread poller; bool online,faceView; float lastPacket,yaw,zoom=1.02f,blendStart;
 Vector3 lastMouse; BridgeState state; string currentCue="",currentExpression="native";
 int[] faceBones; Dictionary<string,float[]> poses=new Dictionary<string,float[]>(); float[] neutral;
 Vector3[] oldT,oldS; Quaternion[] oldQ; float[] faceWeights; string[] faceNames;
 bool manual; float manualStart; Vector2 scroll; string status="Connecting to local bridge...";

 static string JsonString(string s){return "\""+(s??"").Replace("\\","\\\\").Replace("\"","\\\"")+"\"";}
 static float[] ReadPose(string path,int bones){using(var r=new BinaryReader(File.OpenRead(path))){
  if(Encoding.ASCII.GetString(r.ReadBytes(8))!="ENFMOT1\0"||r.ReadInt32()!=bones)throw new Exception("Face pose contract");
  int frames=r.ReadInt32();float fps=r.ReadSingle();if(frames<1||fps<=0)throw new Exception("Face pose header");
  var values=new float[bones*10];for(int i=0;i<values.Length;i++)values[i]=r.ReadSingle();return values;
 }}
 void Start(){try{
  var args=Environment.GetCommandLineArgs();int ri=Array.IndexOf(args,"-nativeRoot");root=ri>=0?args[ri+1]:Path.GetDirectoryName(Application.dataPath);
  int ui=Array.IndexOf(args,"-bridgeUrl");if(ui>=0)url=args[ui+1].TrimEnd('/');var u=new Uri(url);if(u.Scheme!="http"||u.Host!="127.0.0.1")throw new Exception("Bridge must use loopback HTTP");
  QualitySettings.skinWeights=SkinWeights.FourBones;QualitySettings.antiAliasing=4;Application.targetFrameRate=60;Application.runInBackground=true;
  body=new GameObject("Original Endfield Si").AddComponent<NativeMotionPlayer>();body.Build(Path.Combine(root,"assets-v1"),Path.Combine(root,"motions"));body.Playing=false;body.enabled=false;
  var f=JsonUtility.FromJson<FacePoseManifest>(File.ReadAllText(Path.Combine(root,"expressions","manifest.json")));faceBones=f.face_bones;
  foreach(var p in f.poses)poses.Add(p.name,ReadPose(Path.Combine(root,"expressions",p.file),body.Bones.Length));neutral=poses[f.neutral];
  oldT=new Vector3[body.Bones.Length];oldS=new Vector3[body.Bones.Length];oldQ=new Quaternion[body.Bones.Length];
  faceNames=new string[poses.Count];poses.Keys.CopyTo(faceNames,0);faceWeights=new float[faceNames.Length];
  view=new GameObject("Character camera").AddComponent<Camera>();view.orthographic=true;view.orthographicSize=zoom;view.clearFlags=CameraClearFlags.SolidColor;view.backgroundColor=new Color(.19f,.22f,.25f);view.nearClipPlane=.01f;view.farClipPlane=50;
  Capture();blendStart=-1;manualStart=Time.realtimeSinceStartup;running=true;poller=new Thread(Poll){IsBackground=true,Name="Local character bridge"};poller.Start();
  Debug.Log("SI_BRIDGE_PLAYER_READY clips="+body.Manifest.clips.Length+" poses="+poses.Count+" bones="+body.Bones.Length);
 }catch(Exception e){Debug.LogException(e);status="Startup failed: "+e.GetType().Name;enabled=false;}}
 void Poll(){while(running){try{
  var req=(HttpWebRequest)WebRequest.Create(url+"/v1/player/state");req.Proxy=null;req.Timeout=1500;req.ReadWriteTimeout=1500;req.KeepAlive=false;
  using(var response=req.GetResponse())using(var reader=new StreamReader(response.GetResponseStream(),Encoding.UTF8)){Interlocked.Exchange(ref latestJson,reader.ReadToEnd());}
 }catch(WebException){}catch(IOException){} if(running)Thread.Sleep(150);}}
 void Ack(){try{
  string data="{\"turn_id\":"+JsonString(state.turn_id)+",\"action\":"+JsonString(state.action)+",\"expression\":"+JsonString(state.expression)+",\"bones\":596}";
  ThreadPool.QueueUserWorkItem(_=>{try{var req=(HttpWebRequest)WebRequest.Create(url+"/v1/player/ack");req.Proxy=null;req.Method="POST";req.ContentType="application/json";req.Timeout=1000;req.KeepAlive=false;byte[] bytes=Encoding.UTF8.GetBytes(data);req.ContentLength=bytes.Length;using(var stream=req.GetRequestStream())stream.Write(bytes,0,bytes.Length);using(var response=req.GetResponse()){} }catch(WebException){}catch(IOException){} });
 }catch(Exception){}}
 void Capture(){for(int i=0;i<body.Bones.Length;i++){oldT[i]=body.Bones[i].localPosition;oldQ[i]=body.Bones[i].localRotation;oldS[i]=body.Bones[i].localScale;}}
 void Switch(int index){Capture();body.Load(index);blendStart=Time.realtimeSinceStartup;}
 void Update(){if(body==null)return;
  if(Input.GetKeyDown(KeyCode.Escape))Application.Quit();if(Input.GetKeyDown(KeyCode.F)){faceView=!faceView;zoom=faceView?.23f:1.02f;}
  string json=Interlocked.Exchange(ref latestJson,null);
  if(json!=null){try{
   var incoming=JsonUtility.FromJson<BridgeState>(json);if(incoming==null||string.IsNullOrEmpty(incoming.motion_file))throw new Exception("Invalid state");
   int index=Array.FindIndex(body.Manifest.clips,c=>c.file==incoming.motion_file);if(index<0)throw new Exception("Unknown motion");
   bool newTurn=state==null||state.sequence!=incoming.sequence;
   if(newTurn)manual=false;
   if(!manual){if(currentCue!=incoming.cue_id||body.Current!=index){Switch(index);currentCue=incoming.cue_id;}state=incoming;}
   lastPacket=Time.realtimeSinceStartup;online=true;status="Local bridge connected";
   if(!manual){Ack();if(newTurn)Debug.Log("SI_BRIDGE_APPLIED turn="+state.turn_id+" action="+state.action+" emotion="+state.emotion+" expression="+state.expression);}
  }catch(Exception e){status="Playback state rejected: "+e.GetType().Name;}}
  if(Time.realtimeSinceStartup-lastPacket>3){online=false;status="Bridge offline; manual preview available";}
  float seconds=manual?Time.realtimeSinceStartup-manualStart:state!=null?state.action_elapsed+(Time.realtimeSinceStartup-lastPacket):Time.realtimeSinceStartup-manualStart;
  float duration=body.Manifest.clips[body.Current].duration;
  if(manual||state==null||state.loop)seconds=duration>0?seconds%duration:0;else seconds=Mathf.Min(seconds,duration);
  body.Apply(seconds);
  // Pose deltas are relative to the exact native face baseline, so an existing
  // animated expression stays in the body layer. Reduce the overlay for clips
  // with substantial original facial animation to preserve that performance.
  string target=(!manual&&state!=null)?state.expression:"native";float amount=(!manual&&state!=null)?state.emotion_intensity:0;
  if(!manual&&state!=null&&state.native_face_active)amount*=.35f;
  float smooth=1-Mathf.Exp(-Time.deltaTime*7);
  for(int k=0;k<faceNames.Length;k++){float desired=faceNames[k]==target?amount:0;faceWeights[k]=Mathf.Lerp(faceWeights[k],desired,smooth);}
  foreach(int i in faceBones){
   int at=i*10;var b=body.Bones[i];Vector3 t=Vector3.zero,s=Vector3.one;Quaternion q=Quaternion.identity;
   var nq=new Quaternion(neutral[at],neutral[at+1],neutral[at+2],neutral[at+3]);
   for(int k=0;k<faceNames.Length;k++){float weight=faceWeights[k];if(weight<.00001f)continue;var p=poses[faceNames[k]];
    t+=new Vector3(p[at+4]-neutral[at+4],p[at+5]-neutral[at+5],p[at+6]-neutral[at+6])*weight;
    q*=Quaternion.Slerp(Quaternion.identity,Quaternion.Inverse(nq)*new Quaternion(p[at],p[at+1],p[at+2],p[at+3]),weight);
    s+=new Vector3(p[at+7]/Mathf.Max(.001f,neutral[at+7])-1,p[at+8]/Mathf.Max(.001f,neutral[at+8])-1,p[at+9]/Mathf.Max(.001f,neutral[at+9])-1)*weight;
   }
   b.localPosition+=t;b.localRotation*=q;b.localScale=Vector3.Scale(b.localScale,new Vector3(Mathf.Max(.05f,s.x),Mathf.Max(.05f,s.y),Mathf.Max(.05f,s.z)));
  }
  float blend=Mathf.SmoothStep(0,1,Mathf.Clamp01((Time.realtimeSinceStartup-blendStart)/.25f));
  if(blend<1)for(int i=0;i<body.Bones.Length;i++){var b=body.Bones[i];b.localPosition=Vector3.Lerp(oldT[i],b.localPosition,blend);b.localRotation=Quaternion.Slerp(oldQ[i],b.localRotation,blend);b.localScale=Vector3.Lerp(oldS[i],b.localScale,blend);}
 }
 void LateUpdate(){if(body==null||view==null)return;
  if(Input.GetMouseButtonDown(1))lastMouse=Input.mousePosition;if(Input.GetMouseButton(1)){yaw+=(Input.mousePosition.x-lastMouse.x)*.35f;lastMouse=Input.mousePosition;}
  zoom=Mathf.Clamp(zoom-Input.mouseScrollDelta.y*.09f,.18f,1.8f);view.orthographicSize=zoom;Vector3 center;
  if(zoom<.4f){var l=Array.Find(body.Bones,b=>b.name=="faceLfIrisJoint");var r=Array.Find(body.Bones,b=>b.name=="faceRtIrisJoint");center=(l.position+r.position)*.5f+new Vector3(0,-.025f,0);}
  else center=body.Bones[0].position+new Vector3(0,.85f,0);
  view.transform.position=center+Quaternion.Euler(0,yaw,0)*new Vector3(0,0,3.2f);view.transform.LookAt(center);
 }
 void OnGUI(){if(body==null)return;
  GUILayout.BeginArea(new Rect(16,16,330,Screen.height-32),GUI.skin.box);GUILayout.Label("Si / LLM emotion + action");GUILayout.Label(status);
  if(state!=null)GUILayout.Label("Emotion: "+state.emotion+" / "+state.expression);GUILayout.Label("F: face view  Right drag: orbit  Esc: exit");
  if(manual&&GUILayout.Button("Resume LLM control")){manual=false;currentCue="";}
  scroll=GUILayout.BeginScrollView(scroll);for(int i=0;i<body.Manifest.clips.Length;i++)if(GUILayout.Button(body.Manifest.clips[i].label)){manual=true;Switch(i);manualStart=Time.realtimeSinceStartup;}
  GUILayout.EndScrollView();GUILayout.EndArea();
  if(state!=null&&!string.IsNullOrEmpty(state.text)){var style=new GUIStyle(GUI.skin.box){fontSize=23,wordWrap=true,alignment=TextAnchor.MiddleCenter};GUI.Box(new Rect(365,Screen.height-150,Screen.width-390,120),state.text,style);}
 }
 void OnDestroy(){running=false;if(poller!=null)poller.Join(1800);}
}
