using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Profiling;
using Unity.Profiling;
using System.Reflection;
using System.Collections;
using System.Collections.Concurrent;
using System.IO;
using System.Threading;
using MGFR.BareHands;

namespace MGFR.StructuredVoiceFinal {
 [DefaultExecutionOrder(3000)]public sealed class ExperiencePerformance:MonoBehaviour {
  [Serializable]public class Metric {public int samples;public float p50,p95,p99,max;}
  [Serializable]public class Summary {
   public string scenario;public Metric frameMs,cpuMs,gpuMs,clothMs,handPhysicsMs,gcAllocatedBytes;
   public Metric cpuMainThreadMs,cpuPresentWaitMs,clothSolveMs,clothProjectionMs,clothMeshMs;
   public int gcCollections,longFrames,frames;public bool frameTimingAvailable,xrDeviceActive;public long managedBytes;
   public string cpuTimingScope="Unity cpuFrameTime includes frame pacing; unavailable GPU samples do not prove the GPU budget";
  }
  public static ExperiencePerformance Instance;
  readonly List<float> frame=new List<float>(1000),cpu=new List<float>(1000),gpu=new List<float>(1000),cloth=new List<float>(1000),hand=new List<float>(1000),allocations=new List<float>(1000);
  readonly List<float> cpuMain=new List<float>(1000),cpuWait=new List<float>(1000),solve=new List<float>(1000),projection=new List<float>(1000),mesh=new List<float>(1000);
  Func<float> solveTime,projectionTime,meshTime;
  readonly FrameTiming[] timings=new FrameTiming[1];NativeClothCoordinator coordinator;BareHandInteraction hands;
  ProfilerRecorder allocation;bool recording;int gcStart,longFrames;string scenario;
  BlockingCollection<string> writes;Thread writer;
  void Awake(){Instance=this;allocation=ProfilerRecorder.StartNew(ProfilerCategory.Memory,"GC Allocated In Frame",1);}
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,"-mgfr-perf-out");if(i<0||i+1>=args.Length)yield break;
   string path=Path.GetFullPath(args[i+1]);
   // The explicit diagnostic destination must be new. No existing log is truncated.
   FileStream file;try{file=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.Read);}catch(IOException){UnityEngine.Debug.LogWarning("MGFR_PERF_LOG_NOT_CREATED");yield break;}
   writes=new BlockingCollection<string>(8);writer=new Thread(()=>{try{using(var output=new StreamWriter(file)){foreach(var row in writes.GetConsumingEnumerable()){output.WriteLine(row);output.Flush();}}}catch(IOException){}}){IsBackground=true,Name="MGFR numeric performance log"};writer.Start();
   MainAvatarActions driver;while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready)yield return null;
   yield return new WaitForSecondsRealtime(5);Begin("live-runtime");
   while(true){yield return new WaitForSecondsRealtime(5);writes.TryAdd(JsonUtility.ToJson(End()));Begin("live-runtime");}
  }
  public void Begin(string name){
   scenario=name;frame.Clear();cpu.Clear();gpu.Clear();cloth.Clear();hand.Clear();allocations.Clear();gcStart=GC.CollectionCount(0);longFrames=0;
   coordinator=FindAnyObjectByType<NativeClothCoordinator>();hands=FindAnyObjectByType<BareHandInteraction>();recording=true;
   cpuMain.Clear();cpuWait.Clear();solve.Clear();projection.Clear();mesh.Clear();
   solveTime=Getter("SolveMilliseconds");projectionTime=Getter("ProjectionMilliseconds");meshTime=Getter("MeshMilliseconds");
  }
  Func<float> Getter(string name){var p=typeof(NativeClothCoordinator).GetProperty(name);return coordinator!=null&&p!=null?(Func<float>)Delegate.CreateDelegate(typeof(Func<float>),coordinator,p.GetGetMethod()):null;}
  void LateUpdate(){
   if(!recording)return;
   float dt=Time.unscaledDeltaTime*1000;frame.Add(dt);if(dt>28)longFrames++;
   FrameTimingManager.CaptureFrameTimings();uint count=FrameTimingManager.GetLatestTimings(1,timings);
   if(count>0){if(timings[0].cpuFrameTime>0)cpu.Add((float)timings[0].cpuFrameTime);if(timings[0].gpuFrameTime>0)gpu.Add((float)timings[0].gpuFrameTime);if(timings[0].cpuMainThreadFrameTime>0)cpuMain.Add((float)timings[0].cpuMainThreadFrameTime);cpuWait.Add((float)timings[0].cpuMainThreadPresentWaitTime);}
   if(coordinator!=null)cloth.Add(coordinator.LastMilliseconds);
   if(hands!=null&&hands.IsReady)hand.Add(hands.Physics.LastMilliseconds);
   if(allocation.Valid&&allocation.Count>0)allocations.Add(allocation.LastValue);
   if(solveTime!=null)solve.Add(solveTime());if(projectionTime!=null)projection.Add(projectionTime());if(meshTime!=null)mesh.Add(meshTime());
  }
  public Summary End(){
   recording=false;return new Summary{scenario=scenario,frameMs=Stats(frame),cpuMs=Stats(cpu),gpuMs=Stats(gpu),clothMs=Stats(cloth),handPhysicsMs=Stats(hand),gcAllocatedBytes=Stats(allocations),cpuMainThreadMs=Stats(cpuMain),cpuPresentWaitMs=Stats(cpuWait),clothSolveMs=Stats(solve),clothProjectionMs=Stats(projection),clothMeshMs=Stats(mesh),gcCollections=GC.CollectionCount(0)-gcStart,longFrames=longFrames,frames=frame.Count,frameTimingAvailable=cpu.Count>0&&gpu.Count>0,xrDeviceActive=UnityEngine.XR.XRSettings.isDeviceActive,managedBytes=Profiler.GetMonoUsedSizeLong()};
  }
  public static Metric Stats(List<float> data){var a=data.ToArray();Array.Sort(a);return new Metric{samples=a.Length,p50=Percentile(a,.5),p95=Percentile(a,.95),p99=Percentile(a,.99),max=a.Length>0?a[a.Length-1]:0};}
  static float Percentile(float[] a,double q){return a.Length>0?a[(int)Math.Ceiling(q*(a.Length-1))]:0;}
  void OnDestroy(){if(writes!=null){if(recording)writes.TryAdd(JsonUtility.ToJson(End()));writes.CompleteAdding();if(writer!=null)writer.Join(1000);}allocation.Dispose();if(Instance==this)Instance=null;}
 }
}
