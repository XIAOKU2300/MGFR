using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace MGFR.BareHands
{
    public sealed class HandTrackingDiagnostics:MonoBehaviour
    {
        [Serializable] sealed class Snapshot
        {
            public string timeMeaning="application-reception-not-camera-exposure";
            public int hand,frame;public string phase;public double received;
            public Pose head;public Pose[] raw,interaction,render;
            public bool[] rawValid,interactionValid,renderValid;
            public float[] radius,lastValid;public JointSampleSource[] source;public JointRadiusSource[] radiusSource;
        }
        readonly Queue<Snapshot> queue=new Queue<Snapshot>(); StreamWriter output;int dropped;float deadline;
        public bool Capturing=>output!=null&&Time.unscaledTime<deadline;
        void Awake()
        {
            var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-hand-diagnostics");
            if(at<0||at+1>=args.Length)return;
            try {Directory.CreateDirectory(args[at+1]);output=new StreamWriter(new FileStream(Path.Combine(args[at+1],"hand-trace-"+DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff")+".jsonl"),FileMode.CreateNew));deadline=Time.unscaledTime+120;}
            catch {Debug.LogWarning("[Hand diagnostics] output unavailable; no existing trace overwritten");}
        }
        public void Capture(int hand,HandFrame raw,HandFrame interaction,HandFrame render)
        {
            if(!Capturing)return;if(queue.Count>=128){dropped++;return;}
            var camera=Camera.main;queue.Enqueue(new Snapshot{hand=hand,frame=raw.UnityFrame,phase=raw.UpdatePhase,received=raw.ReceivedAt,
                head=camera!=null?new Pose(camera.transform.position,camera.transform.rotation):Pose.identity,
                raw=(Pose[])raw.Joints.Clone(),interaction=(Pose[])interaction.Joints.Clone(),render=(Pose[])render.Joints.Clone(),
                rawValid=(bool[])raw.Valid.Clone(),interactionValid=(bool[])interaction.Valid.Clone(),renderValid=(bool[])render.Valid.Clone(),
                radius=(float[])render.Radius.Clone(),lastValid=(float[])interaction.LastValidTime.Clone(),source=(JointSampleSource[])interaction.JointSource.Clone(),radiusSource=(JointRadiusSource[])render.RadiusSource.Clone()});
        }
        void Update()
        {
            if(output==null)return;int count=0;
            while(queue.Count>0&&count++<32)output.WriteLine(JsonUtility.ToJson(queue.Dequeue()));
            if(Time.unscaledTime>=deadline&&queue.Count==0){output.Dispose();output=null;Debug.Log("[Hand diagnostics] capture complete droppedRecords="+dropped);}
        }
        void OnDestroy(){if(output!=null){while(queue.Count>0)output.WriteLine(JsonUtility.ToJson(queue.Dequeue()));output.Dispose();}}
    }
}
