using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Skins;
namespace MGFR.StructuredVoiceFinal {
 [DefaultExecutionOrder(2700)]public sealed class NativeAcceptance:MonoBehaviour {
  [Serializable]public class Phase {public string name;public int frames,abnormalJumps;public float maxSpeed,maxStep,maxWristStep,clothMaxOffset,clothMeanMs,clothResidual;public string bone;}
  [Serializable]public class Report {public bool pass,finishedAfterAudio,returnedToIdle,interruptedToIdle,skinPhasePreserved,physicsContacts,idleKeepsLooping;public int mappedBones,clipReadsStart,clipReadsEnd;public Phase[] phases;public string mode="Desktop Unity native Humanoid bake/standard Animation, live cloth/physics, synthetic speech signals; no headset or remote LLM";}
  MainAvatarActions driver;SiSkinSwitcher skins;Transform[] bones;Quaternion[] previous;Vector3[] positions;bool capture;float last;Phase current;string output;int sequence=1000,round;readonly List<Phase> phases=new List<Phase>();
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-native-out")+1];Directory.CreateDirectory(output);AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   float end=Time.realtimeSinceStartup+60;while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>end){Debug.LogError("NATIVE_REVIEW_TIMEOUT");Application.Quit(2);yield break;}yield return null;}
   skins=FindAnyObjectByType<SiSkinSwitcher>();round=FindAnyObjectByType<DialogueClient>().CurrentRound;driver.ReviewOverride=true;driver.ReviewSpeaking=false;QualitySettings.vSyncCount=0;Application.targetFrameRate=60;
   var selected=new List<Transform>();var names=new HashSet<string>{"腰","上半身","上半身2","首","頭","左腕","右腕","左ひじ","右ひじ","左手首","右手首","左足","右足","左ひざ","右ひざ","左足D","右足D"};foreach(var b in skins.Loader.Renderer.bones)if(names.Contains(b.name))selected.Add(b);bones=selected.ToArray();previous=new Quaternion[bones.Length];positions=new Vector3[bones.Length];
   var report=new Report{mappedBones=driver.MappedBones,clipReadsStart=driver.ClipReads};yield return new WaitForSeconds(1);
   Begin("native-idle");yield return new WaitForSeconds(5);End();report.idleKeepsLooping=driver.ClipPlaying&&current.maxSpeed>.05f;Snapshot("idle");
   Begin("dialogue");Plan("talk_hands");yield return new WaitForSeconds(2.5f);Snapshot("talk");Plan("think");yield return new WaitForSeconds(2.5f);Snapshot("think");Plan("arms_crossed");yield return new WaitForSeconds(3);Snapshot("arms-crossed");driver.ReviewSpeaking=false;yield return new WaitForSeconds(3);End();
   Begin("llm-sequence");driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=round,emotion="happy",expression_variant="happy_soft",actions=new[]{new ActionCue{name="wave",at=0,duration=4.166667f},new ActionCue{name="introduce",at=4.166667f,duration=5.633334f}}});driver.ReviewSpeaking=true;yield return new WaitForSeconds(2);driver.ReviewSpeaking=false;yield return new WaitForSeconds(.5f);driver.ReviewSpeaking=true;yield return new WaitForSeconds(6.5f);driver.ReviewSpeaking=false;yield return new WaitForSeconds(2.5f);End();
   Begin("finish-and-interrupt");Plan("wave");yield return new WaitForSeconds(1);driver.ReviewSpeaking=false;yield return new WaitForSeconds(.8f);report.finishedAfterAudio=driver.CurrentAction=="wave";yield return new WaitForSeconds(3.5f);report.returnedToIdle=driver.CurrentAction=="idle"&&driver.BodyWeight<.01f;
   Plan("think");yield return new WaitForSeconds(1);driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=round,emotion="neutral",expression_variant="native",actions=new ActionCue[0]});driver.ReviewSpeaking=false;yield return new WaitForSeconds(1);report.interruptedToIdle=driver.CurrentAction=="idle";End();
   Begin("skin-switch");Plan("think");yield return new WaitForSeconds(1);float clock=driver.MotionClock;bool first=skins.TrySelect("original");yield return null;report.skinPhasePreserved=first&&Mathf.Abs(driver.MotionClock-clock)<.15f;yield return new WaitForSeconds(.7f);bool second=skins.TrySelect("swimsuit");yield return new WaitForSeconds(1);report.skinPhasePreserved&=second;driver.ReviewSpeaking=false;yield return new WaitForSeconds(4);End();Snapshot("returned-idle");
   var cloth=FindAnyObjectByType<NativeClothCoordinator>();report.physicsContacts=cloth!=null&&cloth.AddedCapsules>=20;report.clipReadsEnd=driver.ClipReads;report.phases=phases.ToArray();report.pass=report.idleKeepsLooping&&report.finishedAfterAudio&&report.returnedToIdle&&report.interruptedToIdle&&report.skinPhasePreserved&&report.physicsContacts&&report.clipReadsEnd==report.clipReadsStart;
   foreach(var p in phases)if(p.abnormalJumps>0)report.pass=false;
   using(var w=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))w.Write(JsonUtility.ToJson(report,true));Debug.Log("NATIVE_ACCEPTANCE_"+(report.pass?"PASS":"FAIL"));Application.Quit(report.pass?0:5);
  }
  void Plan(string name){driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=round,emotion="neutral",expression_variant="neutral_relaxed",actions=new[]{new ActionCue{name=name,at=0,duration=30}}});driver.ReviewSpeaking=true;}
  void Begin(string name){current=new Phase{name=name};phases.Add(current);for(int i=0;i<bones.Length;i++){previous[i]=bones[i].localRotation;positions[i]=skins.Loader.transform.InverseTransformPoint(bones[i].position);}last=Time.unscaledTime;capture=true;}
  void End(){capture=false;if(current.frames>0)current.clothMeanMs/=current.frames;Debug.Log("NATIVE_PHASE "+current.name+" jumps="+current.abnormalJumps+" speed="+current.maxSpeed+" bone="+current.bone+" clothMs="+current.clothMeanMs);}
  void LateUpdate(){if(!capture)return;float dt=Time.unscaledTime-last;if(dt<=0)return;last=Time.unscaledTime;current.frames++;
   if(current.frames==1){for(int i=0;i<bones.Length;i++){previous[i]=bones[i].localRotation;positions[i]=skins.Loader.transform.InverseTransformPoint(bones[i].position);}return;}
   for(int i=0;i<bones.Length;i++){float angle=Quaternion.Angle(previous[i],bones[i].localRotation),speed=angle/dt;if(speed>current.maxSpeed){current.maxSpeed=speed;current.bone=bones[i].name;}current.maxStep=Mathf.Max(current.maxStep,angle);if(!float.IsFinite(speed)||speed>1800&&angle>30)current.abnormalJumps++;var p=skins.Loader.transform.InverseTransformPoint(bones[i].position);if(bones[i].name.Contains("手首"))current.maxWristStep=Mathf.Max(current.maxWristStep,Vector3.Distance(p,positions[i]));positions[i]=p;previous[i]=bones[i].localRotation;}
   var cloth=FindAnyObjectByType<NativeClothCoordinator>();if(cloth!=null){current.clothMeanMs+=cloth.LastMilliseconds;current.clothResidual=Mathf.Max(current.clothResidual,cloth.ResidualPenetration);}var old=FindAnyObjectByType<MGFR.Skins.ClothPhysics.SwimsuitClothRuntime>();if(old!=null&&old.Solver!=null)current.clothMaxOffset=Mathf.Max(current.clothMaxOffset,old.Solver.MaximumOffset);
  }
  void Snapshot(string name){var camera=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var old=camera.targetTexture;var pos=camera.transform.position;var rot=camera.transform.rotation;bool ortho=camera.orthographic;float size=camera.orthographicSize;
   var center=skins.Loader.transform.position+Vector3.up*.88f;camera.orthographic=true;camera.orthographicSize=1.05f;camera.transform.position=center+Vector3.back*3;camera.transform.LookAt(center);var rt=new RenderTexture(720,900,24);camera.targetTexture=rt;camera.Render();var active=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(720,900,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,720,900),0,0);image.Apply();using(var f=new FileStream(Path.Combine(output,name+".png"),FileMode.CreateNew)){var b=image.EncodeToPNG();f.Write(b,0,b.Length);}RenderTexture.active=active;camera.targetTexture=old;camera.transform.SetPositionAndRotation(pos,rot);camera.orthographic=ortho;camera.orthographicSize=size;Destroy(image);rt.Release();Destroy(rt);
  }
 }
}
