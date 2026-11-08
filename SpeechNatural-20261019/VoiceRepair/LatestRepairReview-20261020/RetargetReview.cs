using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Skins;
namespace MGFR.StructuredVoiceFinal {
 public sealed class RetargetReview:MonoBehaviour {
  [Serializable] public class ClipResult {public string name;public int samples,violations;public float minimum=1,worstTime;}
  [Serializable] public class Report {public string scope="Current main package; no microphone, remote model or headset";public bool pass;public int totalSamples,totalViolations;public float torsoScale;public ClipResult[] clips;}
  MainAvatarActions driver;SiCharacterLoader loader;string output;
  IEnumerator Start(){
   var auto=FindAnyObjectByType<MGFR.Dialogue.AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;AudioListener.volume=0;
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-retarget-out")+1];if(Directory.Exists(output))throw new Exception("Review output exists");Directory.CreateDirectory(output);
   float end=Time.realtimeSinceStartup+45;while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>end){Application.Quit(2);yield break;}yield return null;}
   loader=FindAnyObjectByType<SiSkinSwitcher>().Loader;driver.ReviewOverride=true;driver.ReviewSpeaking=true;
   var data=args[Array.IndexOf(args,"-mgfr-avatar-data")+1];var motions=JsonUtility.FromJson<MotionList>(File.ReadAllText(Path.Combine(data,"motions/manifest.json")));
   var results=new List<ClipResult>();var report=new Report();int sequence=1000;
   foreach(var clip in motions.clips){
    var result=new ClipResult{name=clip.name};driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=-1,emotion="neutral",expression_variant="neutral_relaxed",emotion_intensity=.4f,speech_duration=120,actions=new[]{new ActionCue{name=clip.name,at=0,duration=clip.duration+1}}});
    int count=Mathf.CeilToInt(clip.duration*15);for(int sample=0;sample<=count;sample++){
     float time=Mathf.Min(clip.duration,sample/15f);driver.ReviewAt(time);float clearance=driver.ArmClearance();
     if(clearance<result.minimum){result.minimum=clearance;result.worstTime=time;}
     if(clearance<-.02f)result.violations++;result.samples++;
     foreach(var bone in loader.Renderer.bones)if(float.IsNaN(bone.localRotation.x)||float.IsInfinity(bone.localRotation.x))throw new Exception("Invalid bone pose");
    }
    if(clip.name=="talk_hands"||clip.name=="think"||clip.name=="arms_crossed"||clip.name=="introduce"||clip.name=="wave"||clip.name=="scratch_head_start"){
     driver.ReviewAt(result.worstTime);Snapshot(clip.name+"-front.png",false);Snapshot(clip.name+"-side.png",true);
    }
    results.Add(result);report.totalSamples+=result.samples;report.totalViolations+=result.violations;
    Debug.Log("RETARGET_CLIP "+clip.name+" samples="+result.samples+" violations="+result.violations+" min="+result.minimum+" worst="+result.worstTime);yield return null;
   }
   report.clips=results.ToArray();report.pass=report.totalViolations==0;
   using(var file=new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew))using(var writer=new StreamWriter(file))writer.Write(JsonUtility.ToJson(report,true));
   Debug.Log("RETARGET_REVIEW "+(report.pass?"PASS":"FAIL")+" samples="+report.totalSamples+" violations="+report.totalViolations);Application.Quit(report.pass?0:5);
  }
  void Snapshot(string name,bool side){
   var camera=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var old=camera.targetTexture;var position=camera.transform.position;var rotation=camera.transform.rotation;bool ortho=camera.orthographic;float size=camera.orthographicSize;
   Vector3 center=loader.transform.position+Vector3.up*.88f;camera.orthographic=true;camera.orthographicSize=1;camera.transform.position=center+(side?Vector3.left:Vector3.back)*3;camera.transform.LookAt(center);
   var rt=new RenderTexture(720,900,24);camera.targetTexture=rt;camera.Render();RenderTexture.active=rt;var image=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();RenderTexture.active=null;
   using(var file=new FileStream(Path.Combine(output,name),FileMode.CreateNew)){var bytes=image.EncodeToPNG();file.Write(bytes,0,bytes.Length);}camera.targetTexture=old;camera.transform.SetPositionAndRotation(position,rotation);camera.orthographic=ortho;camera.orthographicSize=size;Destroy(image);rt.Release();Destroy(rt);
  }
 }
}
