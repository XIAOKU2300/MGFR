using System;
using System.IO;
using UnityEngine;

namespace MGFR.BareHands
{
    // Changes only a new render-frame copy. Physics and grabbing never consume this frame.
    public static class HandVisualCalibration
    {
        [Serializable] public sealed class Hand
        { public Vector3 positionMetres,rotationDegrees;public float palmWidth=1,palmThickness=1;public float[] fingerWidth={1,1,1,1,1}; public float[] tipLength={1,1,1,1,1}; }
        [Serializable] public sealed class Config { public int version=1;public Hand left=new Hand(),right=new Hand(); }
        static Config config; public static Config Current {get{Load();return config;}}
        static void Load()
        {
            if(config!=null)return;config=new Config();var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-hand-calibration");
            if(at>=0&&at+1<args.Length)
            {
                try {var parsed=JsonUtility.FromJson<Config>(File.ReadAllText(args[at+1]));if(parsed!=null&&parsed.version==1&&parsed.left!=null&&parsed.right!=null){Validate(parsed.left);Validate(parsed.right);config=parsed;}else throw new InvalidDataException();}
                catch {Debug.LogWarning("[Hand calibration] invalid version or values; using identity calibration");}
            }
            Debug.Log("[Hand calibration] version=1 coordinateSpace=wrist-local visualCopyOnly=True defaults=identity");
        }
        static void Validate(Hand h)
        {
            if(!float.IsFinite(h.positionMetres.sqrMagnitude)||h.positionMetres.magnitude>.035f||!float.IsFinite(h.rotationDegrees.sqrMagnitude)||h.rotationDegrees.magnitude>20||
               !float.IsFinite(h.palmWidth)||h.palmWidth<.8f||h.palmWidth>1.15f||!float.IsFinite(h.palmThickness)||h.palmThickness<.65f||h.palmThickness>1.25f||
               h.fingerWidth==null||h.fingerWidth.Length!=5||h.tipLength==null||h.tipLength.Length!=5)throw new InvalidDataException();
            for(int i=0;i<5;i++)if(!float.IsFinite(h.fingerWidth[i])||h.fingerWidth[i]<.65f||h.fingerWidth[i]>1.15f||!float.IsFinite(h.tipLength[i])||h.tipLength[i]<.75f||h.tipLength[i]>1.1f)throw new InvalidDataException();
        }
        public static Hand Settings(int hand)=>hand==0?Current.left:Current.right;
        public static int Finger(int joint)=>joint<6?0:joint<11?1:joint<16?2:joint<21?3:4;
        public static void Apply(int hand,HandFrame source,HandFrame result)
        {
            HandJointSource.CopyFrame(source,result);if(!source.Valid[1])return;var c=Settings(hand);var wrist=source.Joints[1];var inverse=Quaternion.Inverse(wrist.rotation);var turn=Quaternion.Euler(c.rotationDegrees);
            for(int i=0;i<26;i++)if(source.Valid[i])
            {
                var local=inverse*(source.Joints[i].position-wrist.position);
                result.Joints[i]=new Pose(wrist.position+wrist.rotation*(turn*local+c.positionMetres),wrist.rotation*turn*inverse*source.Joints[i].rotation);
                if(i>=2)result.Radius[i]=source.Radius[i]*c.fingerWidth[Finger(i)];
            }
        }
    }
}
