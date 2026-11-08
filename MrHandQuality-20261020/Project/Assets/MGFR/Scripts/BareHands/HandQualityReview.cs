using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.XR.Hands;

namespace MGFR.BareHands
{
    public sealed class HandQualityReview:MonoBehaviour
    {
        readonly List<string> checks=new List<string>();bool pass=true;
        void Check(string label,bool value){checks.Add(label+"="+value);pass&=value;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-hand-quality-review")>=0)new GameObject("Hand quality regression").AddComponent<HandQualityReview>();}
        public static HandFrame Frame(float time)
        {
            var f=new HandFrame{Timestamp=time,Tracked=true,ValidCount=26,ObservedCount=26};
            f.Joints[1]=new Pose(new Vector3(0,1,0),Quaternion.identity);f.Joints[0]=new Pose(new Vector3(0,1.04f,0),Quaternion.identity);
            for(int i=0;i<26;i++){f.Valid[i]=f.Observed[i]=true;f.Radius[i]=i<2?.018f:.008f;f.LastValidTime[i]=time;f.JointSource[i]=JointSampleSource.Replay;f.RadiusSource[i]=JointRadiusSource.PalmEstimate;}
            for(int finger=0;finger<5;finger++)
            {
                int first=finger==0?2:6+(finger-1)*5;int count=finger==0?4:5;
                for(int j=0;j<count;j++)f.Joints[first+j]=new Pose(new Vector3((finger-2)*.018f,1.025f+j*.024f,0),Quaternion.identity);
            }
            return f;
        }
        IEnumerator Start()
        {
            yield return new WaitForSeconds(1);
            var source=gameObject.AddComponent<HandJointSource>();source.Replay=true;
            var f=Frame(1);source.AcceptSample(0,f,XRHandSubsystem.UpdateType.Dynamic,1);
            Check("nativeRenderIsUnsmoothed",Vector3.Distance(source.RenderFrames[0].Joints[10].position,f.Joints[10].position)<.000001f);
            f=Frame(1.02f);f.Valid[10]=false;f.ValidCount--;source.AcceptSample(0,f,XRHandSubsystem.UpdateType.Dynamic,1.02);
            Check("missingTipDisablesOnlyItsRenderSegment",source.RenderFrames[0].Tracked&&!source.RenderFrames[0].Valid[10]&&source.RenderFrames[0].Valid[15]);
            Check("heldTipCannotStartPinch",!source.Frames[0].CanStartPinch&&source.Frames[0].JointSource[10]==JointSampleSource.Held);
            f=Frame(1.09f);f.Valid[10]=false;f.ValidCount--;source.AcceptSample(0,f,XRHandSubsystem.UpdateType.Dynamic,1.09);
            Check("jointAgeNotRefreshedByOtherJoints",!source.Frames[0].Valid[10]);
            f=Frame(1.11f);f.Joints[15].position+=Vector3.right;source.AcceptSample(0,f,XRHandSubsystem.UpdateType.BeforeRender,1.11);
            Check("badJointRejectedOtherFingersRemain",!source.RenderFrames[0].Valid[15]&&source.RenderFrames[0].Valid[10]);
            source.ExpireRender(1.18f);Check("staleRenderCannotOcclude",!source.RenderFrames[0].Tracked);
            f=Frame(1.2f);source.AcceptSample(0,f,XRHandSubsystem.UpdateType.Dynamic,1.2);Check("reentryRecovers",source.RenderFrames[0].Tracked);
            f=Frame(1.22f);for(int i=0;i<26;i++)f.Joints[i].position+=Vector3.right;
            source.AcceptSample(0,f,XRHandSubsystem.UpdateType.BeforeRender,1.22);Check("relocationUsesNewMeasuredPoseWithoutOldHistory",source.RenderFrames[0].Tracked&&source.RenderFrames[0].Joints[1].position.x>.99f&&source.Relocations==1);
            f.Timestamp=1.24f;source.AcceptSample(0,f,XRHandSubsystem.UpdateType.Dynamic,1.24);Check("relocationRecoversWithoutOldOffset",source.RenderFrames[0].Tracked&&source.RenderFrames[0].Joints[1].position.x>.99f);
            source.PublishControllerFrame(1,Frame(1).Joints,true);source.InvalidateHand(0);Check("leftLossPreservesRightController",source.IsControllerPose(1)&&source.Frames[1].Tracked);
            f=Frame(2);var visual=new HandFrame();HandVisualCalibration.Apply(0,f,visual);var first=visual.Joints[10].position;HandVisualCalibration.Apply(0,f,visual);
            Check("calibrationDoesNotAccumulate",Vector3.Distance(first,visual.Joints[10].position)<.000001f&&Vector3.Distance(f.Joints[10].position,first)<.000001f);
            var material=new Material(Resources.Load<Shader>("HandDepth"));var envelope=new HandOcclusionEnvelope(material);envelope.Update(f,true,0,2);
            bool finite=true;foreach(var v in envelope.Mesh.vertices)finite&=float.IsFinite(v.sqrMagnitude);Check("envelopeFinite",finite);
            f.Valid[10]=false;envelope.Update(f,true,0,2.02);var vertices=envelope.Mesh.vertices;bool collapsed=true;for(int i=6*96;i<7*96;i++)collapsed&=Vector3.Distance(vertices[i],f.Joints[1].position)<.000001f;
            Check("missingTipCollapsesItsGeometry",collapsed);envelope.Dispose();Destroy(material);
            var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-quality-output");if(at>=0&&at+1<args.Length){Directory.CreateDirectory(args[at+1]);File.WriteAllLines(Path.Combine(args[at+1],"hand-quality-checks.txt"),checks);}
            Debug.Log("HAND_QUALITY_REVIEW "+string.Join(" ",checks)+" PASS="+pass);Application.Quit(pass?0:1);
        }
    }
}
