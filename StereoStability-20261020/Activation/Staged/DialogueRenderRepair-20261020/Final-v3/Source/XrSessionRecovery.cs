using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Threading;
using UnityEngine;
using UnityEngine.XR;
using UnityEngine.XR.Management;
using UnityEngine.XR.OpenXR;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Skins;
using MGFR.Skins.ClothPhysics;
using MGFR.StructuredVoiceFinal;

namespace MGFR.Repairs {
 [DefaultExecutionOrder(-32000)]
 public sealed class XrSessionRecovery:MonoBehaviour {
  [Serializable]sealed class Entry {public string utc,eventName,state;public float elapsed,peakFrameMs;public int xrExitRequests,recoveryAttempts,errors;public long managedBytes;}
  StreamWriter log;readonly object logLock=new object();Coroutine recovery;bool closing,reviewOnly,lastRunning;int errors;float nextStatus,peakFrame;
  readonly List<XRDisplaySubsystem> displays=new List<XRDisplaySubsystem>();
  public int XrExitRequests {get;private set;}public int RecoveryAttempts {get;private set;}public string State {get;private set;}="starting";
  public int ErrorCount=>Volatile.Read(ref errors);
  public static void Install(){
   var args=Environment.GetCommandLineArgs();bool review=Array.IndexOf(args,"-mgfr-stability-review")>=0;
   if(Array.IndexOf(args,"-mgfr-noxr")>=0&&!review)return;
   if(FindAnyObjectByType<XrSessionRecovery>()!=null)return;
   var go=new GameObject("XR session continuity and exit diagnostics");DontDestroyOnLoad(go);go.AddComponent<XrSessionRecovery>();
   if(review)new GameObject("Stereo stability acceptance").AddComponent<StereoStabilityReview>();
  }
  void Awake(){
   var args=Environment.GetCommandLineArgs();reviewOnly=Array.IndexOf(args,"-mgfr-noxr")>=0;
   int index=Array.IndexOf(args,"-logFile");string directory=index>=0&&index+1<args.Length?Path.GetDirectoryName(Path.GetFullPath(args[index+1])):Application.persistentDataPath;
   try{Directory.CreateDirectory(directory);string path=Path.Combine(directory,"session-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fffffff")+".jsonl");log=new StreamWriter(new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read)){AutoFlush=true};}catch(IOException){}
   Application.runInBackground=true;
   OpenXRRuntime.wantsToQuit+=XrWantsToQuit;OpenXRRuntime.wantsToRestart+=XrWantsToRestart;
   Application.wantsToQuit+=UserWantsToQuit;Application.quitting+=OnQuitting;Application.logMessageReceivedThreaded+=OnLog;
   State=reviewOnly?"desktop_review":"watching";Record("installed");
  }
  bool XrWantsToQuit(){
   if(closing)return true;
   XrExitRequests++;State=reviewOnly?"review_exit_cancelled":"xr_exit_cancelled";Record("xr_runtime_requested_exit");
   // An XR session ending must not discard the running conversation/window.
   // Window Close and the application's own Quit still follow UserWantsToQuit.
   if(!reviewOnly&&recovery==null)recovery=StartCoroutine(Recover());
   return false;
  }
  bool XrWantsToRestart(){Record("xr_runtime_requested_restart");return !closing;}
  bool UserWantsToQuit(){closing=true;State="application_closing";Record("application_quit_accepted");return true;}
  void OnQuitting(){closing=true;State="application_closed";Record("application_quitting");}
  void OnLog(string message,string stack,LogType type){if(type==LogType.Exception||type==LogType.Error||type==LogType.Assert)Interlocked.Increment(ref errors);}
  bool DisplayRunning(){displays.Clear();SubsystemManager.GetSubsystems(displays);foreach(var display in displays)if(display.running)return true;return false;}
  IEnumerator Recover(){
   // Let OpenXR finish its own shutdown coroutine before touching this app's loader.
   yield return new WaitForSecondsRealtime(2);
   for(int attempt=0;attempt<3&&!closing;attempt++){
    if(DisplayRunning()){State="xr_connected";Record("xr_recovered");recovery=null;yield break;}
    RecoveryAttempts++;State="xr_reconnecting";Record("xr_reconnect_attempt");
    try{
     var manager=XRGeneralSettings.Instance!=null?XRGeneralSettings.Instance.Manager:null;
     if(manager!=null){if(manager.activeLoader!=null){manager.StopSubsystems();manager.DeinitializeLoader();}manager.InitializeLoaderSync();if(manager.activeLoader!=null)manager.StartSubsystems();}
    }catch(Exception exception){Record("xr_reconnect_failed_"+exception.GetType().Name);}
    yield return new WaitForSecondsRealtime(2*(attempt+1));
   }
   State=DisplayRunning()?"xr_connected":"waiting_for_headset";Record(State);recovery=null;
  }
  void Update(){
   peakFrame=Mathf.Max(peakFrame,Time.unscaledDeltaTime*1000);
   if(Time.unscaledTime<nextStatus)return;nextStatus=Time.unscaledTime+5;
   bool running=DisplayRunning();if(running!=lastRunning){lastRunning=running;Record(running?"xr_display_started":"xr_display_stopped");}else Record("heartbeat");
   peakFrame=0;
  }
  void OnApplicationFocus(bool focused){Record(focused?"focus_acquired":"focus_lost");}
  void OnApplicationPause(bool paused){Record(paused?"application_paused":"application_resumed");}
  void Record(string name){
   try{lock(logLock){if(log==null)return;log.WriteLine(JsonUtility.ToJson(new Entry{utc=DateTime.UtcNow.ToString("O"),eventName=name,state=State,elapsed=Time.realtimeSinceStartup,peakFrameMs=peakFrame,xrExitRequests=XrExitRequests,recoveryAttempts=RecoveryAttempts,errors=ErrorCount,managedBytes=GC.GetTotalMemory(false)}));}}catch(IOException){}
  }
  void OnDestroy(){
   OpenXRRuntime.wantsToQuit-=XrWantsToQuit;OpenXRRuntime.wantsToRestart-=XrWantsToRestart;Application.wantsToQuit-=UserWantsToQuit;Application.quitting-=OnQuitting;Application.logMessageReceivedThreaded-=OnLog;
   lock(logLock){log?.Dispose();log=null;}
  }
 }

 [DefaultExecutionOrder(-31000)]
 public sealed class StereoStabilityReview:MonoBehaviour {
  [Serializable]sealed class Result {public bool pass,gpuStereoPass;public int frames,actions,skinChanges,scaleChanges,sdkExitRequestsCancelled,nonFiniteParticles,errors,clipReadsStart,clipReadsEnd;public float seconds,peakFrameMs;public string mode="Actual active-runtime code; desktop synthetic speech/actions, cloth, outfit and scale changes; actual OpenXR quit event injected, headset reconnect not simulated";}
  IEnumerator Start(){
   var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;AudioListener.volume=0;QualitySettings.vSyncCount=0;Application.targetFrameRate=60;
   var args=Environment.GetCommandLineArgs();string output=args[Array.IndexOf(args,"-mgfr-stability-out")+1];
   float timeout=Time.realtimeSinceStartup+50;MainAvatarActions driver;SiSkinSwitcher skins;XrSessionRecovery guard;
   while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready||(skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||(guard=FindAnyObjectByType<XrSessionRecovery>())==null){if(Time.realtimeSinceStartup>timeout){Application.Quit(2);yield break;}yield return null;}
   var control=skins.Loader.GetComponent<SiCharacterController>();driver.ReviewOverride=true;
   while(FindAnyObjectByType<MGFR.GesturePanel.GesturePanelRuntime>()==null||!FindAnyObjectByType<MGFR.GesturePanel.GesturePanelRuntime>().Ready){if(Time.realtimeSinceStartup>timeout){Application.Quit(2);yield break;}yield return null;}
   bool gpu=StereoMaterialGpuReview.Run(Path.Combine(Path.GetDirectoryName(output),"Stereo"));
   yield return new WaitForSecondsRealtime(1);
   var report=new Result{clipReadsStart=driver.ClipReads,gpuStereoPass=gpu};float start=Time.realtimeSinceStartup,nextAction=0,nextSkin=12,nextScale=10,nextExit=5;
   var shouldQuit=typeof(OpenXRRuntime).GetMethod("ShouldQuit",BindingFlags.Static|BindingFlags.NonPublic);
   string[] actions={"talk_hands","think","wave","introduce","arms_crossed"};float[] scales={.5f,1f,2f,1f};
   while(Time.realtimeSinceStartup-start<100){
    float elapsed=Time.realtimeSinceStartup-start;report.frames++;report.peakFrameMs=Mathf.Max(report.peakFrameMs,Time.unscaledDeltaTime*1000);
    if(elapsed>=nextAction){string action=actions[report.actions%actions.Length];if(!driver.IsReviewedAction(action))throw new InvalidOperationException("Required action unavailable");driver.SetReviewPlan(new SpeechPlan{sequence=30000+report.actions,voice_round=-1,emotion="happy",expression_variant="happy_soft",speech_duration=3,actions=new[]{new ActionCue{name=action,at=0,duration=2.5f}}});driver.ReviewSpeaking=true;report.actions++;nextAction+=4;}
    if(elapsed>=nextSkin){if(!skins.TrySelect(report.skinChanges%2==0?"original":"swimsuit"))throw new InvalidOperationException("Outfit unavailable");report.skinChanges++;nextSkin+=12;}
    if(elapsed>=nextScale&&control!=null){control.RestoreRoomPlacement(control.PlanarPosition,control.Yaw,scales[report.scaleChanges%scales.Length],control.GroundHeight);report.scaleChanges++;nextScale+=10;}
    if(elapsed>=nextExit&&report.sdkExitRequestsCancelled<3){if(shouldQuit==null||!(shouldQuit.Invoke(null,null) is bool cancelled)||cancelled)throw new InvalidOperationException("XR exit was not cancelled");report.sdkExitRequestsCancelled++;nextExit+=30;}
    if(report.frames%30==0){var cloth=FindAnyObjectByType<SwimsuitClothRuntime>();if(cloth!=null&&cloth.Solver!=null)foreach(var particle in cloth.Solver.Particles)if(!float.IsFinite(particle.position.x)||!float.IsFinite(particle.position.y)||!float.IsFinite(particle.position.z))report.nonFiniteParticles++;}
    yield return null;
   }
   report.seconds=Time.realtimeSinceStartup-start;report.errors=guard.ErrorCount;report.clipReadsEnd=driver.ClipReads;
   report.pass=report.gpuStereoPass&&report.frames>900&&report.actions>=24&&report.skinChanges>=8&&report.scaleChanges>=9&&report.sdkExitRequestsCancelled==3&&report.nonFiniteParticles==0&&report.errors==0&&report.clipReadsStart==report.clipReadsEnd;
   using(var stream=new FileStream(output,FileMode.CreateNew))using(var writer=new StreamWriter(stream))writer.Write(JsonUtility.ToJson(report,true));
   Debug.Log("MGFR_STEREO_STABILITY_"+(report.pass?"PASS":"FAIL"));Application.Quit(report.pass?0:5);
  }
 }
}
