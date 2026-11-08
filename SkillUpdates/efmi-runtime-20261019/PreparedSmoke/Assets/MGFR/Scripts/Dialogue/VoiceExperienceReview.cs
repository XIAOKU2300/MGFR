using System;
using System.IO;
using System.Text;
using System.Collections;
using UnityEngine;
using MGFR.Experience;

namespace MGFR.Dialogue
{
 public sealed class VoiceExperienceReview:MonoBehaviour
 {
  [Serializable]class Report
  {
   public bool pass,automaticSession,audioPlayed,returnedToIdle;
   public string source="RECORDED_AUDIO_REAL_ASR_LLM_TTS_NOT_HEADSET_MIC",recognized,reply;
   public long acceptedSamples,playedSamples,droppedSamples;public int underruns;
   public int inputRate,sentMicrophoneFrames,droppedAudioFrames;public float peakBlend,maxBlendStep,finalBlend,peakLevel;
   public int motionSentences,motionGestures,framesOver28ms;public float peakGestureDegrees,maxFrameMs,meanPhysicsMs,maxPhysicsMs;
  }
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-voice-review")>=0)new GameObject("Voice experience review").AddComponent<VoiceExperienceReview>();}
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string path=args[Array.IndexOf(args,"-mgfr-voice-input")+1],dir=args[Array.IndexOf(args,"-mgfr-voice-dir")+1];Directory.CreateDirectory(dir);
   bool skipTiming=false;int observedFrames=0;float physicsTotal=0;var physics=FindAnyObjectByType<MGFR.PhysicsRig.PmxSecondaryPhysics>();
   float deadline=Time.realtimeSinceStartup+85;AutomaticVoiceSession voice;IdleMotionPlayer idle;
   while((voice=FindAnyObjectByType<AutomaticVoiceSession>())==null||!voice.SessionStarted||(idle=FindAnyObjectByType<IdleMotionPlayer>())==null)
   {if(Time.realtimeSinceStartup>deadline){Debug.LogError("Voice startup timed out");Application.Quit(1);yield break;}yield return null;}
   idle=FindAnyObjectByType<IdleMotionPlayer>();var client=FindAnyObjectByType<DialogueClient>();var report=new Report{automaticSession=voice.SessionStarted};
   byte[] pcm=null;int rate=0,channels=0;
   using(var reader=new BinaryReader(File.OpenRead(path)))
   {
    reader.ReadBytes(12);
    while(reader.BaseStream.Position+8<=reader.BaseStream.Length)
    {
     string id=Encoding.ASCII.GetString(reader.ReadBytes(4));int size=reader.ReadInt32();long start=reader.BaseStream.Position;
     if(id=="fmt "){if(reader.ReadInt16()!=1)throw new InvalidDataException("Expected PCM WAV");channels=reader.ReadInt16();rate=reader.ReadInt32();reader.BaseStream.Position=start+14;if(reader.ReadInt16()!=16)throw new InvalidDataException("Expected 16-bit WAV");}
     if(id=="data"){pcm=reader.ReadBytes(size);break;}reader.BaseStream.Position=start+size+(size&1);
    }
   }
   int count=rate/50;var frame=new float[count*channels];report.inputRate=rate;
   Snapshot(Path.Combine(dir,"idle-before.png"));
   int total=pcm.Length/2;float next=Time.realtimeSinceStartup;bool snapped=false;float previous=idle.SpeakingBlend;
   for(int offset=-count*channels*25;offset<total+count*channels*40;offset+=count*channels)
   {
    Array.Clear(frame,0,frame.Length);
    if(offset>=0)for(int i=0;i<frame.Length&&offset+i<total;i++)frame[i]=(short)(pcm[(offset+i)*2]|pcm[(offset+i)*2+1]<<8)/32768f;
    voice.SendSamples(frame,channels,rate);next+=.02f;
    while(Time.realtimeSinceStartup<next){Observe();yield return null;}
   }
   while(Time.realtimeSinceStartup<deadline)
   {
    Observe();
    if(report.audioPlayed&&!client.IsSpeaking&&client.QueuedSamples==0&&idle.SpeakingBlend<.02f&&!string.IsNullOrEmpty(client.ReplyText))break;
    yield return null;
   }
   report.recognized=client.LastAsrText;report.reply=client.ReplyText;report.sentMicrophoneFrames=voice.SentFrames;report.droppedAudioFrames=client.DroppedAudioFrames;report.finalBlend=idle.SpeakingBlend;report.returnedToIdle=report.audioPlayed&&report.finalBlend<.02f;
   report.motionSentences=idle.Gestures.StartedSentences;report.motionGestures=idle.Gestures.StartedGestures;report.peakGestureDegrees=idle.Gestures.PeakDegrees;report.meanPhysicsMs=physicsTotal/Mathf.Max(1,observedFrames);
   var audio=client.GetComponent<DialogueAudioOutput>();report.acceptedSamples=audio.AcceptedSamples;report.playedSamples=audio.PlayedSamples;report.droppedSamples=audio.DroppedSamples;report.underruns=audio.UnderrunEvents;
   report.pass=report.droppedSamples==0&&report.acceptedSamples==report.playedSamples&&report.underruns==0&&report.automaticSession&&report.audioPlayed&&report.peakBlend>.8f&&report.returnedToIdle&&report.maxBlendStep<.15f&&!string.IsNullOrEmpty(report.recognized)&&!string.IsNullOrEmpty(report.reply)&&report.droppedAudioFrames==0&&report.motionSentences>0;
   Snapshot(Path.Combine(dir,"idle-after.png"));File.WriteAllText(Path.Combine(dir,"voice-review.json"),JsonUtility.ToJson(report,true));Debug.Log("[MGFR voice review] "+JsonUtility.ToJson(report));Application.Quit(report.pass?0:1);
   void Observe()
   {
    if(!skipTiming)
    {
     float ms=Time.unscaledDeltaTime*1000;report.maxFrameMs=Mathf.Max(report.maxFrameMs,ms);if(ms>28)report.framesOver28ms++;
     if(physics!=null){physicsTotal+=physics.LastMilliseconds;report.maxPhysicsMs=Mathf.Max(report.maxPhysicsMs,physics.LastMilliseconds);observedFrames++;}
    }
    skipTiming=false;
    report.audioPlayed|=client.IsSpeaking;report.peakLevel=Mathf.Max(report.peakLevel,client.CurrentLevel);report.peakBlend=Mathf.Max(report.peakBlend,idle.SpeakingBlend);report.maxBlendStep=Mathf.Max(report.maxBlendStep,Mathf.Abs(idle.SpeakingBlend-previous));previous=idle.SpeakingBlend;
    if(!snapped&&client.IsSpeaking&&idle.SpeakingBlend>.7f){Snapshot(Path.Combine(dir,"speaking.png"));snapped=true;skipTiming=true;}
   }
  }
  static void Snapshot(string path)
  {
   var camera=Camera.main;var target=new RenderTexture(800,800,24);var old=camera.targetTexture;camera.targetTexture=target;camera.Render();RenderTexture.active=target;
   var image=new Texture2D(800,800,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,800,800),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());RenderTexture.active=null;camera.targetTexture=old;target.Release();Destroy(target);Destroy(image);
  }
 }
}
