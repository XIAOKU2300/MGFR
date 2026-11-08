using System;
using System.IO;
using System.Collections;
using UnityEngine;
using MGFR.Dialogue;
using MGFR.Character;
namespace MGFR.StructuredActions {
 public sealed class MainNetworkReview:MonoBehaviour {
  [Serializable] class Result {public bool pass,audioPlayed,bodyAndSadTogether,replyOnlyText,returnedToIdle;public float peakBody,peakEmotion,peakLevel;public string mode="Real main player, real WebSocket/PCM/audio cursor, synthetic LLM/TTS, no microphone or external model";}
  IEnumerator Start(){AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   var args=Environment.GetCommandLineArgs();string output=args[Array.IndexOf(args,"-mgfr-actions-network-out")+1];if(File.Exists(output))throw new Exception("Output exists");
   float timeout=Time.realtimeSinceStartup+35;MainAvatarActions driver;DialogueClient voice;
   while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready||(voice=FindAnyObjectByType<DialogueClient>())==null){if(Time.realtimeSinceStartup>timeout){Application.Quit(2);yield break;}yield return null;}
   voice.Connect();while(voice.State!=DialogueState.Connected||string.IsNullOrEmpty(voice.ServerVersion)){if(Time.realtimeSinceStartup>timeout){Debug.LogError("NETWORK_REVIEW_CONNECT_TIMEOUT");Application.Quit(3);yield break;}yield return null;}
   voice.StartSession();while(voice.ServerState!="listening"){if(Time.realtimeSinceStartup>timeout){Application.Quit(4);yield break;}yield return null;}
   voice.SendTextPrompt("测试情绪动作结构化回复");var result=new Result();float end=Time.realtimeSinceStartup+22;bool heard=false;
   while(Time.realtimeSinceStartup<end){
    result.audioPlayed|=voice.IsSpeaking;heard|=voice.IsSpeaking;result.peakBody=Mathf.Max(result.peakBody,driver.BodyWeight);result.peakEmotion=Mathf.Max(result.peakEmotion,driver.EmotionWeight);result.peakLevel=Mathf.Max(result.peakLevel,voice.CurrentLevel);
    result.bodyAndSadTogether|=voice.IsSpeaking&&driver.BodyWeight>.5f&&driver.EmotionWeight>.25f&&driver.CurrentEmotion=="sad"&&driver.CurrentAction=="think";
    if(heard&&!voice.IsSpeaking&&voice.QueuedSamples==0&&driver.BodyWeight<.01f&&driver.EmotionWeight<.01f){result.returnedToIdle=true;break;}yield return null;
   }
   result.replyOnlyText=voice.ReplyText=="我有一点难过，不过会陪你慢慢说。";result.pass=result.audioPlayed&&result.bodyAndSadTogether&&result.replyOnlyText&&result.returnedToIdle;
   using(var f=new FileStream(output,FileMode.CreateNew))using(var w=new StreamWriter(f))w.Write(JsonUtility.ToJson(result,true));
   Debug.Log("MGFR_MAIN_NETWORK_REVIEW_"+(result.pass?"PASS":"FAIL")+" body="+result.peakBody+" emotion="+result.peakEmotion+" audioLevel="+result.peakLevel);Application.Quit(result.pass?0:5);
  }
 }
}
