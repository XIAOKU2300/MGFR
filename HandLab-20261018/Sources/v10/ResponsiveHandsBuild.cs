using System;
using UnityEngine;

namespace MGFR.BareHands
{
 public static class ResponsiveHandsBuild
 {
  static HandFrame Frame(Vector3 wrist)
  {
   var f=new HandFrame{Tracked=true,ValidCount=26,ObservedCount=26};
   for(int i=0;i<26;i++){f.Valid[i]=f.Observed[i]=true;f.Joints[i]=new Pose(wrist+new Vector3((i%5)*.015f,i*.004f,0),Quaternion.identity);}
   f.Joints[1]=new Pose(wrist,Quaternion.identity);return f;
  }
  public static void Build()
  {
   var p=new HandRenderPrediction();double time=1;float original=0,predicted=0;
   for(int i=0;i<90;i++)
   {
    float x=i/72f;var f=Frame(Vector3.right*x);p.Apply(f,time);time+=1d/72;
    if(i>5){var expected=Vector3.right*(x+HandRenderPrediction.LeadSeconds);original+=Vector3.Distance(expected,Vector3.right*x);predicted+=Vector3.Distance(expected,f.Joints[1].position);}
   }
   if(predicted>original*.15f)throw new Exception("Constant-speed visual prediction did not reduce lag");
   float stopX=89/72f;var stop=Frame(Vector3.right*stopX);p.Apply(stop,time);time+=1d/72;
   if(Vector3.Distance(stop.Joints[1].position,Vector3.right*stopX)>.0001f)throw new Exception("Prediction must stop when observed motion stops");
   var reverse=Frame(Vector3.right*(stopX-.02f));p.Apply(reverse,time);time+=1d/72;
   if(reverse.Joints[1].position.x>stopX-.02f+.0001f)throw new Exception("Prediction must not continue through a reversal");
   p.Reset();float max=0;
   for(int i=0;i<40;i++){float x=i%2==0?.001f:-.001f;var f=Frame(Vector3.right*x);p.Apply(f,time);time+=1d/72;max=Mathf.Max(max,Mathf.Abs(f.Joints[1].position.x-x));}
   if(max>.0001f)throw new Exception("Alternating jitter must not be predicted");
   var lost=Frame(Vector3.zero);lost.Tracked=false;p.Apply(lost,time);
   var timer=System.Diagnostics.Stopwatch.StartNew();for(int i=0;i<1000;i++){var f=Frame(Vector3.right*(i/72f));p.Apply(f,10+i/72d);}timer.Stop();
   Debug.Log($"[MGFR render prediction checks] PASS horizonMs=18 constantSpeedErrorRatio={predicted/original:F3} immediateStop=True reversalStops=True jitterNotAmplified=True meanCpuMs={timer.Elapsed.TotalMilliseconds/1000:F4}");
   OcclusionHandsBuild.Build();
  }
 }
}
