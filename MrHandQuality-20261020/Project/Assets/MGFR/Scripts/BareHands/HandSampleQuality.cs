using System;
using UnityEngine;

namespace MGFR.BareHands
{
    public enum JointSampleSource:byte { Invalid, SDK, Held, Controller, Replay }
    public enum JointRadiusSource:byte { Unknown, Device, PalmEstimate }
    public sealed class HandSampleQuality
    {
        static readonly int[] Parent={1,-1,1,2,3,4,1,6,7,8,9,1,11,12,13,14,1,16,17,18,19,1,21,22,23,24};
        readonly Vector3[] previousLocal=new Vector3[26];
        readonly float[] seen=new float[26]; readonly bool[] initialized=new bool[26];
        Vector3 previousWrist; Quaternion previousWristRotation; float previousTime; bool hadWrist;
        public int Rejected {get;private set;} public int Relocations {get;private set;}
        public void Reset(){Array.Clear(initialized,0,26);hadWrist=false;}
        public bool Filter(HandFrame sample)
        {
            bool relocated=false;
            for(int i=0;i<26;i++)if(sample.Valid[i])
            {
                var p=sample.Joints[i];float q=Quaternion.Dot(p.rotation,p.rotation);
                if(!float.IsFinite(p.position.sqrMagnitude)||!float.IsFinite(q)||q<.25f||q>4)Reject(sample,i);
                else {p.rotation=Quaternion.Normalize(p.rotation);sample.Joints[i]=p;}
            }
            if(!sample.Valid[1]){Reset();return false;}
            var wrist=sample.Joints[1];float dt=sample.Timestamp-previousTime;
            if(hadWrist&&dt>=0&&dt<.1f&&(Vector3.Distance(previousWrist,wrist.position)>.25f||Quaternion.Angle(previousWristRotation,wrist.rotation)>100))
            {Reset();Relocations++;relocated=true;}
            var inverse=Quaternion.Inverse(wrist.rotation);
            for(int i=0;i<26;i++)if(sample.Valid[i]&&i!=1)
            {
                var local=inverse*(sample.Joints[i].position-wrist.position);int parent=Parent[i];
                float distance=parent>=0&&sample.Valid[parent]?Vector3.Distance(sample.Joints[i].position,sample.Joints[parent].position):0;
                bool segment=distance>0&&(distance<.002f||distance>(parent==1?.16f:.095f));
                float elapsed=sample.Timestamp-seen[i];
                bool jump=initialized[i]&&elapsed>=0&&elapsed<.1f&&Vector3.Distance(local,previousLocal[i])>Mathf.Max(.045f,elapsed*3f);
                if(local.magnitude>.27f||segment||jump){Reject(sample,i);continue;}
                previousLocal[i]=local;seen[i]=sample.Timestamp;initialized[i]=true;
            }
            previousWrist=wrist.position;previousWristRotation=wrist.rotation;previousTime=sample.Timestamp;hadWrist=true;
            for(int i=0;i<26;i++)if(sample.Valid[i])
            {sample.LastValidTime[i]=sample.Timestamp;sample.JointSource[i]=JointSampleSource.SDK;sample.Observed[i]=true;}
            return relocated;
        }
        void Reject(HandFrame sample,int i){sample.Valid[i]=sample.Observed[i]=false;sample.JointSource[i]=JointSampleSource.Invalid;sample.ValidCount--;Rejected++;}
    }
}
