using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Skins;
namespace MGFR.StructuredVoiceFinal {
 [DefaultExecutionOrder(2700)]public sealed class NativeCatalogReview:MonoBehaviour {
  [Serializable]public class ClipResult {public string name;public int frames,jumps;public float maxSpeed,residual,sourcePeak,threshold;}
  [Serializable]public class Result {public bool pass;public int clips,frames;public ClipResult[] results;public string scope="19 production voice actions, real Unity playback and cloth; source-relative speed limits; native fast gestures retained";}
  [Serializable]class SourceSkin {public string skin;public float sourcePeak;}
  [Serializable]class SourceClip {public string name;public SourceSkin[] skins;}
  [Serializable]class SourceAudit {public SourceClip[] clips;}
  MainAvatarActions driver;SiSkinSwitcher skins;Transform[] bones;Quaternion[] previous;ClipResult current;bool capture;float last;int sequence=2000,round;
  IEnumerator Start(){var args=Environment.GetCommandLineArgs();string output=args[Array.IndexOf(args,"-mgfr-native-out")+1];Directory.CreateDirectory(output);AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   float deadline=Time.realtimeSinceStartup+60;while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>deadline){Application.Quit(2);yield break;}yield return null;}
   skins=FindAnyObjectByType<SiSkinSwitcher>();var selected=new List<Transform>();var names=new HashSet<string>{"腰","上半身","上半身2","首","頭","左腕","右腕","左ひじ","右ひじ","左手首","右手首","左足D","右足D"};foreach(var b in skins.Loader.Renderer.bones)if(names.Contains(b.name))selected.Add(b);bones=selected.ToArray();previous=new Quaternion[bones.Length];
   driver.ReviewOverride=true;driver.ReviewSpeaking=true;round=FindAnyObjectByType<DialogueClient>().CurrentRound;QualitySettings.vSyncCount=0;Application.targetFrameRate=60;
   string data=args[Array.IndexOf(args,"-mgfr-avatar-data")+1];var manifest=JsonUtility.FromJson<MotionList>(File.ReadAllText(Path.Combine(data,"motions/manifest.json")));
   var allowed=new HashSet<string>{"scratch_head_start","scratch_head","relaxed_idle","idle_special_2","surprised_pose","talk_hands","ponder","wave","arms_crossed","nod","tsundere","idle","think","settle","shake_head","receive_gift","point","introduce","base_idle"};var results=new List<ClipResult>();var report=new Result{pass=true};
   var audit=JsonUtility.FromJson<SourceAudit>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"native-actions/source-relative-verification.json")));
   foreach(var clip in manifest.clips){if(!allowed.Contains(clip.name))continue;current=new ClipResult{name=clip.name};foreach(var original in audit.clips)if(original.name==clip.name)foreach(var variant in original.skins)current.sourcePeak=Mathf.Max(current.sourcePeak,variant.sourcePeak);current.threshold=Mathf.Max(1800,current.sourcePeak*1.25f+400);results.Add(current);for(int i=0;i<bones.Length;i++)previous[i]=bones[i].localRotation;last=Time.unscaledTime;capture=true;
    driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=round,emotion="neutral",expression_variant="native",actions=new[]{new ActionCue{name=clip.name,at=0,duration=clip.duration}}});yield return new WaitForSeconds(clip.duration+.65f);capture=false;
    report.clips++;report.frames+=current.frames;if(current.jumps>0)report.pass=false;Debug.Log("NATIVE_CATALOG "+clip.name+" frames="+current.frames+" jumps="+current.jumps+" speed="+current.maxSpeed+" residual="+current.residual);
   }
   report.pass&=report.clips==19;report.results=results.ToArray();using(var w=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))w.Write(JsonUtility.ToJson(report,true));Application.Quit(report.pass?0:5);
  }
  void LateUpdate(){if(!capture)return;float dt=Time.unscaledTime-last;if(dt<=0)return;last=Time.unscaledTime;current.frames++;
   for(int i=0;i<bones.Length;i++){float angle=Quaternion.Angle(previous[i],bones[i].localRotation),speed=angle/dt;current.maxSpeed=Mathf.Max(current.maxSpeed,speed);if(current.frames>1&&(!float.IsFinite(speed)||speed>current.threshold&&angle>30))current.jumps++;previous[i]=bones[i].localRotation;}
   var cloth=FindAnyObjectByType<NativeClothCoordinator>();if(cloth!=null)current.residual=Mathf.Max(current.residual,cloth.ResidualPenetration);
  }
 }
}
