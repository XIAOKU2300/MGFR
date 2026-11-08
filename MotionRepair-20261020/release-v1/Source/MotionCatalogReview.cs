using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Skins;
using MGFR.Dialogue;
namespace MGFR.StructuredVoiceFinal {
 [DefaultExecutionOrder(2650)] public sealed class MotionCatalogReview:MonoBehaviour {
  [Serializable] public class ClipResult {public string name;public int frames,spikes;public float maxSpeed,minClearance=1;}
  [Serializable] public class Report {public bool pass;public int supported,blocked,totalFrames;public ClipResult[] clips;public string scope="All enabled authored clips, real Unity frames, original physical layers, no headset or real LLM";}
  MainAvatarActions driver;SiCharacterLoader loader;Transform[] bones;Quaternion[] previous;ClipResult current;bool sampling;string output;float lastTime;
  IEnumerator Start(){
   AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-catalog-out")+1];Directory.CreateDirectory(output);
   float deadline=Time.realtimeSinceStartup+45;while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>deadline){Application.Quit(2);yield break;}yield return null;}
   loader=FindAnyObjectByType<SiSkinSwitcher>().Loader;var selected=new List<Transform>();var names=new HashSet<string>{"上半身","上半身2","下半身","首","頭","左肩","右肩","左腕","右腕","左ひじ","右ひじ","左手首","右手首","左足","右足","左ひざ","右ひざ"};foreach(var b in loader.Renderer.bones)if(names.Contains(b.name))selected.Add(b);bones=selected.ToArray();previous=new Quaternion[bones.Length];
   driver.ReviewOverride=true;driver.ReviewSpeaking=true;QualitySettings.vSyncCount=0;Application.targetFrameRate=60;
   var data=args[Array.IndexOf(args,"-mgfr-avatar-data")+1];var manifest=JsonUtility.FromJson<MotionList>(File.ReadAllText(Path.Combine(data,"motions/manifest.json")));var results=new List<ClipResult>();var report=new Report();int sequence=2000,round=FindAnyObjectByType<DialogueClient>().CurrentRound;
   foreach(var clip in manifest.clips){if(!driver.IsReviewedAction(clip.name)){report.blocked++;continue;}report.supported++;
    current=new ClipResult{name=clip.name};results.Add(current);for(int i=0;i<bones.Length;i++)previous[i]=bones[i].localRotation;lastTime=Time.unscaledTime;sampling=true;
    driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=round,emotion="neutral",expression_variant="native",actions=new[]{new ActionCue{name=clip.name,at=0,duration=clip.duration}}});
    yield return new WaitForSeconds(clip.duration+.65f);sampling=false;report.totalFrames+=current.frames;
    Debug.Log("CATALOG_MOTION "+clip.name+" frames="+current.frames+" spikes="+current.spikes+" maxSpeed="+current.maxSpeed+" clearance="+current.minClearance);
   }
   report.clips=results.ToArray();report.pass=report.supported==19;foreach(var clip in results)if(clip.spikes>0)report.pass=false;
   using(var w=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))w.Write(JsonUtility.ToJson(report,true));Debug.Log("CATALOG_CONTINUITY_"+(report.pass?"PASS":"FAIL"));Application.Quit(report.pass?0:5);
  }
  void LateUpdate(){if(!sampling)return;float dt=Time.unscaledTime-lastTime;if(dt<=0)return;lastTime=Time.unscaledTime;current.frames++;
   for(int i=0;i<bones.Length;i++){float angle=Quaternion.Angle(previous[i],bones[i].localRotation),speed=angle/dt;if(!float.IsFinite(speed)){current.spikes++;continue;}current.maxSpeed=Mathf.Max(current.maxSpeed,speed);if(speed>600&&angle>3)current.spikes++;previous[i]=bones[i].localRotation;}
   current.minClearance=Mathf.Min(current.minClearance,driver.ArmClearance());
  }
 }
}
