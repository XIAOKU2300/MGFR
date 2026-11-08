using System;
using System.IO;
using System.Collections;
using UnityEngine;

namespace MGFR.Dialogue
{
 public sealed class StreamingAudioReview:MonoBehaviour
 {
  [Serializable]class Report
  {
   public bool pass;public string source="SYNTHETIC_PCM_BURST_AND_JITTER_NOT_HEADSET";
   public long burstAccepted,burstPlayed,droppedSamples,jitterAccepted,jitterPlayed;
   public int underruns,maxDspCallbackFrames;public float burstSeconds=8;
  }
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-audio-review")>=0)new GameObject("Streaming audio continuity review").AddComponent<StreamingAudioReview>();}
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string dir=args[Array.IndexOf(args,"-mgfr-audio-dir")+1];Directory.CreateDirectory(dir);
   var audio=gameObject.AddComponent<DialogueAudioOutput>();var report=new Report();audio.BeginStream();
   byte[] Tone(int samples,int offset)
   {
    var bytes=new byte[samples*2];for(int i=0;i<samples;i++){short v=(short)(Math.Sin((i+offset)*Math.PI*2*220/32000)*1800);bytes[i*2]=(byte)v;bytes[i*2+1]=(byte)(v>>8);}return bytes;
   }
   for(int i=0;i<400;i++)audio.Enqueue(Tone(640,i*640),1,32000);
   audio.CompleteStream();report.burstAccepted=audio.AcceptedSamples;
   float deadline=Time.realtimeSinceStartup+12;
   while((audio.PlaybackPending||audio.QueuedSamples>0)&&Time.realtimeSinceStartup<deadline)yield return null;
   report.burstPlayed=audio.PlayedSamples;long before=audio.AcceptedSamples,playedBefore=audio.PlayedSamples;audio.BeginStream();
   // 180 ms of PCM per arrival, with an irregular 70..150 ms network schedule.
   for(int i=0;i<10;i++){audio.Enqueue(Tone(5760,i*5760),1,32000);yield return new WaitForSecondsRealtime(i%3==0?.15f:.07f);}
   audio.CompleteStream();deadline=Time.realtimeSinceStartup+5;
   while((audio.PlaybackPending||audio.QueuedSamples>0)&&Time.realtimeSinceStartup<deadline)yield return null;
   report.jitterAccepted=audio.AcceptedSamples-before;report.jitterPlayed=audio.PlayedSamples-playedBefore;
   report.droppedSamples=audio.DroppedSamples;report.underruns=audio.UnderrunEvents;report.maxDspCallbackFrames=audio.MaxCallbackFrames;
   report.pass=report.burstAccepted==audio.PlaybackRate*8L&&report.burstPlayed==report.burstAccepted&&report.jitterPlayed==report.jitterAccepted&&report.droppedSamples==0&&report.underruns==0&&report.maxDspCallbackFrames>0&&report.maxDspCallbackFrames<audio.PlaybackRate/4;
   File.WriteAllText(Path.Combine(dir,"audio-continuity.json"),JsonUtility.ToJson(report,true));Debug.Log("[MGFR audio continuity] "+JsonUtility.ToJson(report));Application.Quit(report.pass?0:1);
  }
 }
}
