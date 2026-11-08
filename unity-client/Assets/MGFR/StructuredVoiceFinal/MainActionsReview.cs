using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Skins;
namespace MGFR.StructuredVoiceFinal {
 public sealed class MainActionsReview:MonoBehaviour {
  MainAvatarActions driver;SiCharacterLoader loader;string output;readonly List<string> checks=new List<string>();
  IEnumerator Start(){var auto=FindAnyObjectByType<MGFR.Dialogue.AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-actions-review-out")+1];if(Directory.Exists(output))throw new Exception("Review output exists");Directory.CreateDirectory(output);
   float limit=Time.realtimeSinceStartup+35;while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>limit){Debug.LogError("MAIN_REVIEW_TIMEOUT");Application.Quit(2);yield break;}yield return null;}
   loader=FindAnyObjectByType<SiSkinSwitcher>().Loader;driver.ReviewOverride=true;driver.ReviewSpeaking=false;
   int round=FindAnyObjectByType<MGFR.Dialogue.DialogueClient>().CurrentRound;
   driver.SetReviewPlan(new SpeechPlan{sequence=1,voice_round=round,emotion="sad",expression_variant="sad_soft",emotion_intensity=.6f,actions=new[]{new ActionCue{name="think",at=0,duration=5}}});
   yield return new WaitForSeconds(.6f);if(driver.BodyWeight>.01f)Fail("gesture moved before audible playback");checks.Add("waits for actual playback");
   driver.ReviewSpeaking=true;yield return new WaitForSeconds(1.3f);
   if(driver.BodyWeight<.99f||driver.EmotionWeight<.5f)Fail("body/emotion did not activate together");
   checks.Add("sad and think simultaneously active");Snapshot("00-sad-think.png",false);Snapshot("00-sad-face.png",true);
   int seq=2;
   foreach(string id in new[]{"talk_hands","introduce","think","ponder","arms_crossed","point","surprised_pose","scratch_head_start","relax_react","settle"}){
    driver.SetReviewPlan(new SpeechPlan{sequence=seq++,voice_round=round,emotion="happy",expression_variant="happy_soft",emotion_intensity=.4f,actions=new[]{new ActionCue{name=id,at=0,duration=30}}});
    yield return new WaitForSeconds(1.1f);CheckFinite();Snapshot("body-"+id+".png",false);checks.Add("rendered "+id);
   }
   foreach(string emotion in new[]{"neutral","happy","sad","angry","surprised","shy","thinking","affection"}){
    var poses=JsonUtility.FromJson<EmotionPoses>(File.ReadAllText(Path.Combine(args[Array.IndexOf(args,"-mgfr-avatar-data")+1],"expressions.json")));
    foreach(var pose in poses.poses)if(pose.emotion==emotion){driver.SetReviewPlan(new SpeechPlan{sequence=seq++,voice_round=round,emotion=emotion,expression_variant=pose.name,emotion_intensity=.7f,actions=new ActionCue[0]});yield return new WaitForSeconds(.7f);CheckFinite();Snapshot("face-"+pose.name+".png",true);checks.Add("rendered "+pose.name);}
   }
   driver.ReviewSpeaking=false;yield return new WaitForSeconds(1.1f);if(driver.BodyWeight>.01f||driver.EmotionWeight>.01f)Fail("did not return to idle");checks.Add("smooth return to idle");
   using(var file=new FileStream(Path.Combine(output,"checks.txt"),FileMode.CreateNew))using(var writer=new StreamWriter(file))writer.WriteLine(string.Join("\n",checks));
   Debug.Log("MGFR_MAIN_ACTION_REVIEW_PASS checks="+checks.Count+" mapped="+driver.MappedBones);Application.Quit(0);
  }
  void CheckFinite(){foreach(var bone in loader.Renderer.bones){var q=bone.localRotation;var p=bone.localPosition;if(float.IsNaN(q.x)||float.IsInfinity(q.x)||float.IsNaN(p.x))Fail("non-finite pose");}}
  void Fail(string text){Debug.LogError("MAIN_REVIEW_FAILED "+text);Application.Quit(3);throw new Exception(text);}
  void Snapshot(string name,bool face){var camera=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var old=camera.targetTexture;var position=camera.transform.position;var rotation=camera.transform.rotation;bool ortho=camera.orthographic;float size=camera.orthographicSize;
   var bones=loader.Renderer.bones;var head=Array.Find(bones,b=>b.name=="頭");Vector3 center=face?head.position+loader.transform.TransformVector(new Vector3(0,.035f,0)):loader.transform.position+Vector3.up*.88f;
   camera.orthographic=true;camera.orthographicSize=face?.2f:1.0f;camera.transform.position=center+Vector3.back*3;camera.transform.LookAt(center);
   var rt=new RenderTexture(face?420:800,face?460:1000,24);camera.targetTexture=rt;camera.Render();RenderTexture.active=rt;var image=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();RenderTexture.active=null;
   using(var f=new FileStream(Path.Combine(output,name),FileMode.CreateNew)){var bytes=image.EncodeToPNG();f.Write(bytes,0,bytes.Length);}camera.targetTexture=old;camera.transform.SetPositionAndRotation(position,rotation);camera.orthographic=ortho;camera.orthographicSize=size;Destroy(image);rt.Release();Destroy(rt);
  }
 }
}
