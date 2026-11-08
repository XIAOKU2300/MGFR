using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Skins;
using MGFR.Dialogue;

namespace MGFR.StructuredVoiceFinal {
 [DefaultExecutionOrder(2600)]
 public sealed class MotionContinuityReview:MonoBehaviour {
  [Serializable] public class Metric {public string phase;public int frames,spikes;public float maxDegreesPerSecond,maxStep,maxWristMeters,maxFrameMs;public string worstBone;}
  [Serializable] public class Result {public bool pass;public string scope="Desktop Unity continuous frames; original skin/cloth/foot layers active; no headset/microphone/external LLM";public int clipsReadAtStart,clipsReadAtEnd;public Metric[] phases;public string[] components;public bool returnedToIdle,finishedGestureAfterAudio,interruptReturned;}
  MainAvatarActions driver;SiCharacterLoader loader;Transform[] tracked;Quaternion[] previous;Vector3[] lastWrist;string output;StreamWriter frames;Metric metric;bool capture;int seq=500,round;float lastTime;readonly List<Metric> metrics=new List<Metric>();
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-motion-out")+1];Directory.CreateDirectory(output);
   AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   float deadline=Time.realtimeSinceStartup+45;
   while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>deadline){Debug.LogError("MOTION_REVIEW_TIMEOUT");Application.Quit(2);yield break;}yield return null;}
   loader=FindAnyObjectByType<SiSkinSwitcher>().Loader;round=FindAnyObjectByType<DialogueClient>().CurrentRound;
   driver.ReviewOverride=true;driver.ReviewSpeaking=false;Application.targetFrameRate=60;QualitySettings.vSyncCount=0;
   var names=new HashSet<string>{"センター","上半身","上半身2","下半身","首","頭","左肩","右肩","左腕","右腕","左ひじ","右ひじ","左手首","右手首","左足","右足","左ひざ","右ひざ"};
   var bones=new List<Transform>();foreach(var b in loader.Renderer.bones)if(names.Contains(b.name))bones.Add(b);tracked=bones.ToArray();previous=new Quaternion[tracked.Length];lastWrist=new Vector3[tracked.Length];
   var result=new Result{clipsReadAtStart=driver.ClipReads};var components=new List<string>();foreach(var c in FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))if(c!=null&&c.enabled)components.Add(c.GetType().FullName);result.components=components.ToArray();
   frames=new StreamWriter(new FileStream(Path.Combine(output,"frames.csv"),FileMode.CreateNew));frames.WriteLine("phase,time,dt,bone,angle,speed,positionStep");
   yield return new WaitForSeconds(1);
   Begin("idle");yield return new WaitForSeconds(7);End();Snapshot("idle");
   Begin("dialogue");
   Plan("talk_hands",0);yield return new WaitForSeconds(3);Snapshot("talk-hands");
   Plan("think",0);yield return new WaitForSeconds(2);Snapshot("think");
   Plan("arms_crossed",0);yield return new WaitForSeconds(3);Snapshot("arms-crossed");
   driver.ReviewSpeaking=false;yield return new WaitForSeconds(6);End();
   Begin("llm-sequence");
   driver.SetReviewPlan(new SpeechPlan{sequence=seq++,voice_round=round,emotion="happy",expression_variant="happy_soft",emotion_intensity=.4f,actions=new[]{new ActionCue{name="wave",at=0,duration=4.166667f},new ActionCue{name="introduce",at=4.166667f,duration=3},new ActionCue{name="settle",at=7.166667f,duration=3}}});driver.ReviewSpeaking=true;
   yield return new WaitForSeconds(2);driver.ReviewSpeaking=false;yield return new WaitForSeconds(.45f);driver.ReviewSpeaking=true;
   yield return new WaitForSeconds(5.8f);driver.ReviewSpeaking=false;yield return new WaitForSeconds(5);End();
   Begin("audio-end");Plan("wave",0);yield return new WaitForSeconds(1);driver.ReviewSpeaking=false;yield return new WaitForSeconds(.8f);
   result.finishedGestureAfterAudio=driver.CurrentAction=="wave";yield return new WaitForSeconds(4);
   result.returnedToIdle=driver.CurrentAction=="idle"&&driver.BodyWeight<.01f;End();
   Begin("interrupt");Plan("think",0);yield return new WaitForSeconds(1);
   driver.SetReviewPlan(new SpeechPlan{sequence=seq++,voice_round=round,emotion="neutral",expression_variant="native",actions=new ActionCue[0]});driver.ReviewSpeaking=false;yield return new WaitForSeconds(1.2f);
   result.interruptReturned=driver.CurrentAction=="idle";End();Snapshot("returned-idle");
   result.clipsReadAtEnd=driver.ClipReads;result.phases=metrics.ToArray();result.pass=result.returnedToIdle&&result.interruptReturned&&result.finishedGestureAfterAudio;
   foreach(var m in metrics)if(m.spikes>0)result.pass=false;
   frames.Dispose();using(var w=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))w.Write(JsonUtility.ToJson(result,true));
   Debug.Log("MOTION_CONTINUITY_"+(result.pass?"PASS":"FAIL"));Application.Quit(result.pass?0:5);
  }
  void Plan(string name,float at){driver.SetReviewPlan(new SpeechPlan{sequence=seq++,voice_round=round,emotion="neutral",expression_variant="neutral_relaxed",emotion_intensity=.4f,actions=new[]{new ActionCue{name=name,at=at,duration=30}}});driver.ReviewSpeaking=true;}
  void Begin(string name){metric=new Metric{phase=name};metrics.Add(metric);for(int i=0;i<tracked.Length;i++){previous[i]=tracked[i].localRotation;lastWrist[i]=loader.transform.InverseTransformPoint(tracked[i].position);}lastTime=Time.unscaledTime;capture=true;}
  void End(){capture=false;frames.Flush();Debug.Log("MOTION_PHASE "+metric.phase+" frames="+metric.frames+" maxSpeed="+metric.maxDegreesPerSecond+" spikes="+metric.spikes+" bone="+metric.worstBone);}
  void LateUpdate(){if(!capture)return;float now=Time.unscaledTime,dt=now-lastTime;if(dt<=0)return;lastTime=now;metric.frames++;metric.maxFrameMs=Mathf.Max(metric.maxFrameMs,dt*1000);
   for(int i=0;i<tracked.Length;i++){
    float angle=Quaternion.Angle(previous[i],tracked[i].localRotation);float speed=angle/dt;Vector3 position=loader.transform.InverseTransformPoint(tracked[i].position);float move=Vector3.Distance(position,lastWrist[i]);
    if(speed>metric.maxDegreesPerSecond){metric.maxDegreesPerSecond=speed;metric.worstBone=tracked[i].name;}metric.maxStep=Mathf.Max(metric.maxStep,angle);
    if(tracked[i].name.Contains("手首"))metric.maxWristMeters=Mathf.Max(metric.maxWristMeters,move);
    if(speed>600&&angle>3)metric.spikes++;
    frames.WriteLine(metric.phase+","+now.ToString("F4",System.Globalization.CultureInfo.InvariantCulture)+","+dt.ToString("F4",System.Globalization.CultureInfo.InvariantCulture)+","+tracked[i].name+","+angle.ToString("F4",System.Globalization.CultureInfo.InvariantCulture)+","+speed.ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+","+move.ToString("F5",System.Globalization.CultureInfo.InvariantCulture));
    previous[i]=tracked[i].localRotation;lastWrist[i]=position;
   }
  }
  void Snapshot(string name){var camera=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var old=camera.targetTexture;var pos=camera.transform.position;var rot=camera.transform.rotation;bool ortho=camera.orthographic;float size=camera.orthographicSize;
   var center=loader.transform.position+Vector3.up*.9f;camera.orthographic=true;camera.orthographicSize=1.05f;camera.transform.position=center+Vector3.back*3;camera.transform.LookAt(center);
   var rt=new RenderTexture(720,900,24);camera.targetTexture=rt;camera.Render();var active=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(720,900,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,720,900),0,0);image.Apply();
   using(var f=new FileStream(Path.Combine(output,name+".png"),FileMode.CreateNew)){var bytes=image.EncodeToPNG();f.Write(bytes,0,bytes.Length);}RenderTexture.active=active;camera.targetTexture=old;camera.transform.SetPositionAndRotation(pos,rot);camera.orthographic=ortho;camera.orthographicSize=size;Destroy(image);rt.Release();Destroy(rt);
  }
 }
}
