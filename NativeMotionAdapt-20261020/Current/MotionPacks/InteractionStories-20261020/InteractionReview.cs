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
  [Serializable] public class Entry {public string name,skin,image;public bool played,finite;public float time;}
  [Serializable] public class Report {public bool pass=true;public List<Entry> entries=new List<Entry>();public string scope="Isolated Current runtime, actual Animation sampling and rendered contact sheets. No remote LLM, mic or voice configuration changes.";}
  MainAvatarActions driver;SiSkinSwitcher skins;string output;int seq=9000;
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-native-out")+1];Directory.CreateDirectory(output);AudioListener.volume=0;
   var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   float deadline=Time.realtimeSinceStartup+100;
   while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>deadline){Application.Quit(2);yield break;}yield return null;}
   skins=FindAnyObjectByType<SiSkinSwitcher>();driver.ReviewOverride=true;driver.ReviewSpeaking=true;QualitySettings.vSyncCount=0;Application.targetFrameRate=60;
   var report=new Report();string data=args[Array.IndexOf(args,"-mgfr-avatar-data")+1];
   var manifest=JsonUtility.FromJson<MotionList>(File.ReadAllText(Path.Combine(data,"motions/manifest.json")));
   foreach(var clip in manifest.clips){if(!clip.name.StartsWith("story_")&&!clip.name.StartsWith("common_"))continue;
    driver.SetReviewPlan(new SpeechPlan{sequence=seq++,voice_round=-1,speech_duration=40,emotion="neutral",expression_variant="native",actions=new[]{new ActionCue{name=clip.name,at=0,duration=clip.duration}}});
    yield return new WaitForSeconds(.12f);
    var anim=skins.Loader.GetComponent<Animation>();foreach(AnimationState s in anim)if(anim.IsPlaying(s.name))s.time=clip.duration*.55f;anim.Sample();
    yield return new WaitForEndOfFrame();
    string image=clip.name+".png";var entry=new Entry{name=clip.name,skin=skins.CurrentId,image=image,played=driver.CurrentAction==clip.name,finite=true,time=driver.MotionClock};
    foreach(var b in skins.Loader.Renderer.bones){var p=b.position;var q=b.rotation;if(!float.IsFinite(p.x+p.y+p.z+q.x+q.y+q.z+q.w))entry.finite=false;}
    report.pass&=entry.played&&entry.finite;report.entries.Add(entry);Snapshot(image,false);Debug.Log("INTERACTION_REVIEW "+clip.name+" played="+entry.played);
   }
   var poses=JsonUtility.FromJson<EmotionPoses>(File.ReadAllText(Path.Combine(data,"expressions.json")));
   foreach(var pose in poses.poses){if(!pose.name.StartsWith("story_"))continue;
    driver.SetReviewPlan(new SpeechPlan{sequence=seq++,voice_round=-1,speech_duration=4,emotion=pose.emotion,emotion_intensity=.75f,expression_variant=pose.name,actions=new ActionCue[0]});
    yield return new WaitForSeconds(.5f);yield return new WaitForEndOfFrame();Snapshot("face-"+pose.name+".png",true);
   }
   using(var f=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))f.Write(JsonUtility.ToJson(report,true));Application.Quit(report.pass?0:5);
  }
  void Snapshot(string name,bool face){
   var cam=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var old=cam.targetTexture;var p=cam.transform.position;var q=cam.transform.rotation;bool ortho=cam.orthographic;float size=cam.orthographicSize;
   Vector3 center=face?skins.Loader.Renderer.bones[17].position:skins.Loader.transform.position+Vector3.up*.88f;
   cam.orthographic=true;cam.orthographicSize=face?.24f:1.05f;cam.transform.position=center+Vector3.back*3;cam.transform.LookAt(center);
   int width=face?480:360,height=face?480:450;var rt=new RenderTexture(width,height,24);cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
   var image=new Texture2D(width,height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();var bytes=image.EncodeToPNG();using(var f=new FileStream(Path.Combine(output,name),FileMode.CreateNew))f.Write(bytes,0,bytes.Length);
   RenderTexture.active=active;cam.targetTexture=old;cam.transform.SetPositionAndRotation(p,q);cam.orthographic=ortho;cam.orthographicSize=size;Destroy(image);rt.Release();Destroy(rt);
  }
 }
}
