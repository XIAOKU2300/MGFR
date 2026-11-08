using System;
using System.Collections;
using System.IO;
using System.Reflection;
using UnityEngine;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.BareHands;
using MGFR.PhysicsRig;
using MGFR.Attention;
using MGFR.SmokeTest;

namespace MGFR.Experience
{
 public sealed class PerformanceExperienceReview:MonoBehaviour
 {
  [Serializable]class Report
  {
   public string source="ACTUAL_CHARACTER_SYNTHETIC_PCM_AND_HEAD_MOTION_NOT_HEADSET";
   public bool pass,selfCollisionDisabled,anchorFixed,playedAll,returnedToIdle;
   public int sentences,gestures,maxHitchSubsteps;public long dropped;
   public float wristTravel,gesturePeak,blushPeak,anchorDrift,frameMeanMs,frameP95Ms,physicsMeanMs,physicsMaxMs,discardedCatchupSeconds;
  }
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-performance-review")>=0)new GameObject("Experience performance review").AddComponent<PerformanceExperienceReview>();}
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string dir=args[Array.IndexOf(args,"-mgfr-performance-dir")+1];Directory.CreateDirectory(dir);
   BareHandInteraction hand;while((hand=FindAnyObjectByType<BareHandInteraction>())==null||!hand.IsReady)yield return null;
   var physics=hand.Physics;var loader=physics.Loader;var idle=loader.GetComponent<IdleMotionPlayer>();
   var client=FindAnyObjectByType<DialogueClient>();var audio=client.GetComponent<DialogueAudioOutput>();
   var rig=loader.Renderer.bones;var anchor=loader.transform.position;var report=new Report();
   yield return new WaitForSeconds(.3f);
   report.selfCollisionDisabled=hand.HandProxiesIgnoreEachOther;
   var handle=typeof(DialogueClient).GetMethod("HandleText",BindingFlags.Instance|BindingFlags.NonPublic);
   void Message(string body)=>handle.Invoke(client,new object[]{"{\"v\":1,"+body+"}"});
   Message("\"type\":\"state\",\"round\":1,\"state\":\"speaking\"");
   Message("\"type\":\"asr.final\",\"text\":\"小葱你真可爱，我很喜欢你\"");
   Message("\"type\":\"tts.start\",\"round\":1,\"sentenceIndex\":0,\"text\":\"你好，给你看看，我当然可以陪你聊一会儿。\"");
   int samples=audio.PlaybackRate*6;var pcm=new byte[samples*2];
   for(int i=0;i<samples;i++){short value=(short)(Mathf.Sin(i*2*Mathf.PI*230/audio.PlaybackRate)*1800);pcm[2*i]=(byte)value;pcm[2*i+1]=(byte)(value>>8);}
   audio.BeginStream();audio.Enqueue(pcm,1,audio.PlaybackRate);audio.CompleteStream();
   var follower=Camera.main.GetComponent<XrDeviceFollower>();
   var originalCameraPosition=Camera.main.transform.localPosition;var originalCameraRotation=Camera.main.transform.localRotation;
   var wrist=rig[64].position;var frameTimes=new System.Collections.Generic.List<float>();float start=Time.realtimeSinceStartup,mean=0;int n=0;bool captured=false;
   while(Time.realtimeSinceStartup-start<8)
   {
    float elapsed=Time.realtimeSinceStartup-start;
    if(follower!=null)follower.ApplyTrackedPose(originalCameraPosition+new Vector3(Mathf.Sin(elapsed*2)*.12f,0,0),Quaternion.Euler(0,Mathf.Sin(elapsed)*12,0)*originalCameraRotation);
    report.wristTravel=Mathf.Max(report.wristTravel,Vector3.Distance(wrist,rig[64].position));
    report.blushPeak=Mathf.Max(report.blushPeak,loader.BlushWeight);
    report.anchorDrift=Mathf.Max(report.anchorDrift,Vector3.Distance(anchor,loader.transform.position));
    mean+=physics.LastMilliseconds;n++;report.physicsMaxMs=Mathf.Max(report.physicsMaxMs,physics.LastMilliseconds);
    if(elapsed>.5f)frameTimes.Add(Time.unscaledDeltaTime*1000);
    if(!captured&&elapsed>1.5f){Snapshot(Path.Combine(dir,"speaking-gesture.png"));captured=true;}
    yield return null;
   }
   // A display hitch must not turn into twelve physics steps on the next frame.
   physics.Tick(.12f);report.maxHitchSubsteps=physics.LastSubsteps;report.discardedCatchupSeconds=physics.DiscardedCatchupSeconds;
   report.physicsMeanMs=mean/n;frameTimes.Sort();foreach(float value in frameTimes)report.frameMeanMs+=value;report.frameMeanMs/=frameTimes.Count;report.frameP95Ms=frameTimes[(int)(frameTimes.Count*.95f)];
   report.sentences=idle.Gestures.StartedSentences;report.gestures=idle.Gestures.StartedGestures;report.gesturePeak=idle.Gestures.PeakDegrees;
   report.anchorFixed=report.anchorDrift<.00001f;report.playedAll=audio.AcceptedSamples==audio.PlayedSamples;report.dropped=audio.DroppedSamples;
   report.returnedToIdle=idle.SpeakingBlend<.03f;
   report.pass=report.selfCollisionDisabled&&report.anchorFixed&&report.playedAll&&report.dropped==0&&report.returnedToIdle&&report.sentences==1&&report.gestures>0&&report.gesturePeak>15&&report.wristTravel>.08f&&report.blushPeak>.3f&&report.maxHitchSubsteps<=3;
   File.WriteAllText(Path.Combine(dir,"experience-review.json"),JsonUtility.ToJson(report,true));Debug.Log("[MGFR experience review] "+JsonUtility.ToJson(report));Application.Quit(report.pass?0:1);
  }
  static void Snapshot(string path)
  {
   var camera=Camera.main;var target=new RenderTexture(900,1100,24);var old=camera.targetTexture;var active=RenderTexture.active;
   var position=camera.transform.position;var rotation=camera.transform.rotation;
   var actor=FindAnyObjectByType<SiCharacterLoader>().transform;
   camera.transform.position=actor.position+actor.TransformDirection(Vector3.back)*2.7f+Vector3.up*1.0f;
   camera.transform.LookAt(actor.position+Vector3.up*.95f);
   camera.targetTexture=target;camera.Render();RenderTexture.active=target;
   var image=new Texture2D(900,1100,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,900,1100),0,0);image.Apply();
   File.WriteAllBytes(path,image.EncodeToPNG());RenderTexture.active=active;camera.targetTexture=old;
   camera.transform.SetPositionAndRotation(position,rotation);target.Release();Destroy(target);Destroy(image);
  }
 }
}
