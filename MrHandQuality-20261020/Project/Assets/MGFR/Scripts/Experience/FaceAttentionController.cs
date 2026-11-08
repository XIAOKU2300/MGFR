using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;

namespace MGFR.Attention
{
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(1300)]
    public sealed class FaceAttentionController:MonoBehaviour
    {
        public Transform ViewerTarget;
        public bool TargetAvailable=true;
        public bool RequireTrackedHeadset=true;
        public bool OwnBlink;
        public bool CalibrateIrisPivot=true;
        public int LeftIrisVertices {get;private set;}
        public int RightIrisVertices {get;private set;}
        public Vector3 LeftOpticalPivot=>leftEye!=null?leftEye.parent.TransformPoint(leftPivot):Vector3.zero;
        public Vector3 RightOpticalPivot=>rightEye!=null?rightEye.parent.TransformPoint(rightPivot):Vector3.zero;
        public bool AutoUpdate=true;
        public Action<float> BlushWriter;
        public string Status {get;private set;}="not bound";
        public AttentionOutput Output=>dynamics.Current;
        public double LeftEyeYaw {get;private set;}
        public double RightEyeYaw {get;private set;}
        public double LeftEyePitch {get;private set;}
        public double RightEyePitch {get;private set;}
        public AttentionMode Mode=AttentionMode.Listening;
        public Vector3 LastFixation {get;private set;}
        public bool TrackingValid {get;private set;}
        public Transform HeadBone=>head;
        public Transform LeftEyeBone=>leftEye;
        public Transform RightEyeBone=>rightEye;

        Transform root,neck,head,leftEye,rightEye;
        SkinnedMeshRenderer skin;
        Quaternion neckRest,headRest,leftRest,rightRest,neckRootRest,headRootRest;
        readonly Quaternion faceBasis=Quaternion.LookRotation(Vector3.back,Vector3.up);
        AttentionDynamics dynamics=new AttentionDynamics();
        readonly AngleMotor leftYaw=new AngleMotor(),leftPitch=new AngleMotor(),rightYaw=new AngleMotor(),rightPitch=new AngleMotor();
        readonly string[] morphNames={"にこり","困る","上","口角上げ","口角下げ","笑い","びっくり","まばたき"};
        readonly int[] morphIndices=new int[8];
        readonly float[] morphRest=new float[8];
        Vector3 lastTarget,gesture,leftPosition,rightPosition,leftPivot,rightPivot;
        double gestureUntil=-1;
        bool ready;

        public void Bind(Transform characterRoot,SkinnedMeshRenderer renderer,Transform neckBone,Transform headBone,
            Transform leftEyeBone,Transform rightEyeBone)
        {
            if(characterRoot==null||renderer==null||headBone==null||leftEyeBone==null||rightEyeBone==null)
                throw new ArgumentException("Character root, skin, head and both actual eye bones are required.");
            if(headBone==leftEyeBone||headBone==rightEyeBone||leftEyeBone==rightEyeBone)
                throw new ArgumentException("Head and eye mappings must be distinct.");
            var animator=headBone.GetComponentInParent<Animator>();
            if(animator!=null&&animator.enabled)throw new InvalidOperationException("Resolve Animator/head ownership before binding attention.");
            if(OwnBlink)
            {
                foreach(var component in renderer.GetComponentsInParent<MonoBehaviour>(true))
                    if(component!=null&&component.enabled&&component.GetType().FullName=="MGFR.Character.SiCharacterController")
                        throw new InvalidOperationException("Existing SiCharacterController owns blink. Delegate it explicitly or set OwnBlink=false.");
            }
            Restore();
            root=characterRoot;skin=renderer;neck=neckBone;head=headBone;leftEye=leftEyeBone;rightEye=rightEyeBone;
            neckRest=neck!=null?neck.localRotation:Quaternion.identity;headRest=head.localRotation;
            leftRest=leftEye.localRotation;rightRest=rightEye.localRotation;
            leftPosition=leftEye.localPosition;rightPosition=rightEye.localPosition;
            leftPivot=OpticalPivot(leftEye,out int leftCount);rightPivot=OpticalPivot(rightEye,out int rightCount);
            LeftIrisVertices=leftCount;RightIrisVertices=rightCount;
            neckRootRest=neck!=null?Quaternion.Inverse(root.rotation)*neck.rotation:Quaternion.identity;
            headRootRest=Quaternion.Inverse(root.rotation)*head.rotation;
            int missing=0;
            for(int i=0;i<morphNames.Length;i++)
            {
                morphIndices[i]=skin.sharedMesh.GetBlendShapeIndex(morphNames[i]);
                morphRest[i]=morphIndices[i]>=0?skin.GetBlendShapeWeight(morphIndices[i]):0;
                if(morphIndices[i]<0)missing++;
            }
            ready=true;Status="bound head, neck and binocular gaze; iris supports="+LeftIrisVertices+"/"+RightIrisVertices+"; missing optional shapes="+missing;
            if(ViewerTarget==null&&Camera.main!=null)ViewerTarget=Camera.main.transform;
            ResetDynamics(19);
        }
        public void ResetDynamics(uint seed)
        {
            dynamics=new AttentionDynamics(seed);
            leftYaw.Reset();leftPitch.Reset();rightYaw.Reset();rightPitch.Reset();
            gesture=Vector3.zero;gestureUntil=-1;
        }
        public void BeginSpokenLine(string text,double now)
        {var mood=AttentionDynamics.MatchMood(text);dynamics.SetMood(mood,now);Mode=mood==FaceMood.Thinking?AttentionMode.Thinking:AttentionMode.Speaking;}
        public void EndSpokenLine(){Mode=AttentionMode.Listening;ClearHeadGesture();}
        public void SetMood(FaceMood mood,double now)=>dynamics.SetMood(mood,now);
        public void TriggerBlink(double now)=>dynamics.TriggerBlink(now);
        // Body animation submits its head delta; this component is the only writer of head/neck.
        public void SubmitHeadGesture(Vector3 localEuler,double now)
        {
            if(!Finite(localEuler)||!AttentionMath.Finite(now))return;
            gesture=new Vector3(Mathf.Clamp(localEuler.x,-12,12),Mathf.Clamp(localEuler.y,-12,12),Mathf.Clamp(localEuler.z,-8,8));
            gestureUntil=now+.12;
        }
        public void ClearHeadGesture(){gesture=Vector3.zero;gestureUntil=-1;}
        static bool Finite(Vector3 v)=>AttentionMath.Finite(v.x)&&AttentionMath.Finite(v.y)&&AttentionMath.Finite(v.z);
        void LateUpdate(){if(AutoUpdate)Tick(Time.unscaledTime,Time.unscaledDeltaTime);}

        public void Tick(double now,float delta)
        {
            if(!ready||!AttentionMath.Finite(now)||!AttentionMath.Finite(delta)||delta<0)return;
            var target=ViewerTarget;
            bool tracked=TargetAvailable&&target!=null&&Finite(target.position);
            if(tracked&&RequireTrackedHeadset)
            {
                var device=InputDevices.GetDeviceAtXRNode(XRNode.Head);
                tracked=XRSettings.isDeviceActive&&device.isValid&&device.TryGetFeatureValue(CommonUsages.isTracked,out bool isTracked)&&isTracked;
            }
            Vector3 eyes=(LeftOpticalPivot+RightOpticalPivot)*.5f;
            Quaternion frame=root.rotation*faceBasis;
            Vector3 relative=tracked?Quaternion.Inverse(frame)*(target.position-eyes):Vector3.forward;
            float distance=relative.magnitude;
            double targetYaw=Math.Atan2(relative.x,relative.z)*Mathf.Rad2Deg;
            double targetPitch=-Math.Atan2(relative.y,Math.Sqrt(relative.x*relative.x+relative.z*relative.z))*Mathf.Rad2Deg;
            var input=new AttentionInput{Tracked=tracked,Yaw=targetYaw,Pitch=targetPitch,Distance=distance,Mode=Mode};
            var state=dynamics.Step(input,now,delta);
            TrackingValid=tracked&&Math.Abs(targetYaw)<=82&&Math.Abs(targetPitch)<=60&&distance>=.12f&&distance<=10;
            if(TrackingValid)
            {
                // Keep binocular convergence comfortable when the user gets very close.
                Vector3 direction=(target.position-eyes).normalized;
                lastTarget=eyes+direction*Mathf.Max(.50f,distance);
            }
            LastFixation=lastTarget;
            if(now>gestureUntil)gesture=Vector3.zero;
            if(neck!=null)neck.localRotation=neckRest*Mapped(new Vector3((float)state.NeckPitch,(float)state.NeckYaw,0),neckRootRest);
            head.localRotation=headRest*Mapped(new Vector3((float)state.HeadPitch,(float)state.HeadYaw,(float)state.HeadRoll),headRootRest)*Quaternion.Euler(gesture);
            AimEye(leftEye,leftRest,leftPosition,leftPivot,leftYaw,leftPitch,state,delta,out var ly,out var lp);
            AimEye(rightEye,rightRest,rightPosition,rightPivot,rightYaw,rightPitch,state,delta,out var ry,out var rp);
            LeftEyeYaw=ly;LeftEyePitch=lp;RightEyeYaw=ry;RightEyePitch=rp;
            float blink=OwnBlink?(float)state.Blink:(morphIndices[7]>=0?skin.GetBlendShapeWeight(morphIndices[7])/100f:0);
            var e=state.Expression;
            Weight(0,e.SmileBrows);Weight(1,e.ConcernBrows);Weight(2,e.RaiseBrows);
            Weight(3,e.SmileCorners);Weight(4,e.FrownCorners);
            Weight(5,e.SoftEyes*(1-blink));Weight(6,e.WideEyes*(1-blink));
            if(OwnBlink)Weight(7,blink);
            BlushWriter?.Invoke((float)e.Blush);
        }
        Quaternion Mapped(Vector3 angles,Quaternion boneRootRest)
        {return Quaternion.Inverse(boneRootRest)*faceBasis*Quaternion.Euler(angles)*Quaternion.Inverse(faceBasis)*boneRootRest;}
        void AimEye(Transform eye,Quaternion rest,Vector3 restPosition,Vector3 pivot,AngleMotor yawMotor,AngleMotor pitchMotor,AttentionOutput state,float delta,out double yaw,out double pitch)
        {
            double desiredYaw=0,desiredPitch=0;
            if(state.HasTarget)
            {
                // Recompute AFTER head + neck + speech nod. Eyes compensate for that
                // actual head pose instead of fighting a second head writer.
                Quaternion neutralWorld=eye.parent.rotation*rest*faceBasis;
                Vector3 d=Quaternion.Inverse(neutralWorld)*(lastTarget-eye.parent.TransformPoint(pivot));
                desiredYaw=Math.Atan2(d.x,d.z)*Mathf.Rad2Deg+state.EyeOffsetYaw;
                desiredPitch=-Math.Atan2(d.y,Math.Sqrt(d.x*d.x+d.z*d.z))*Mathf.Rad2Deg+state.EyeOffsetPitch;
                desiredYaw=AttentionMath.Clamp(desiredYaw,-22,22);
                desiredPitch=AttentionMath.Clamp(desiredPitch,-14,14);
            }
            yaw=yawMotor.Step(desiredYaw,delta,35,220,4200);
            pitch=pitchMotor.Step(desiredPitch,delta,35,180,3600);
            eye.localRotation=rest*faceBasis*Quaternion.Euler((float)pitch,(float)yaw,0)*Quaternion.Inverse(faceBasis);
            // Rotate around the calibrated optical center without editing skin data,
            // reparenting, or changing the model's bind poses. Identity is exact rest.
            Quaternion localDelta=eye.localRotation*Quaternion.Inverse(rest);
            eye.localPosition=pivot+localDelta*(restPosition-pivot);
        }
        Vector3 OpticalPivot(Transform eye,out int supportingVertices)
        {
            supportingVertices=0;
            if(!CalibrateIrisPivot)return eye.localPosition;
            var bones=skin.bones;var related=new bool[bones.Length];
            for(int i=0;i<bones.Length;i++)related[i]=bones[i]==eye||bones[i].IsChildOf(eye);
            var vertices=skin.sharedMesh.vertices;var weights=skin.sharedMesh.boneWeights;
            Vector3 sum=Vector3.zero,min=new Vector3(float.MaxValue,float.MaxValue,float.MaxValue),
                max=new Vector3(float.MinValue,float.MinValue,float.MinValue);
            for(int i=0;i<weights.Length;i++)
            {
                var w=weights[i];float influence=(related[w.boneIndex0]?w.weight0:0)+(related[w.boneIndex1]?w.weight1:0)+
                    (related[w.boneIndex2]?w.weight2:0)+(related[w.boneIndex3]?w.weight3:0);
                if(influence<.5f)continue;
                var v=skin.transform.TransformPoint(vertices[i]);sum+=v;min=Vector3.Min(min,v);max=Vector3.Max(max,v);supportingVertices++;
            }
            if(supportingVertices<20||supportingVertices>2000||(max-min).magnitude>.10f)
            {supportingVertices=0;return eye.localPosition;}
            Vector3 irisCenter=sum/supportingVertices;
            Vector3 pivotWorld=irisCenter-(root.rotation*Vector3.back)*.012f;
            if(Vector3.Distance(pivotWorld,eye.position)>.10f){supportingVertices=0;return eye.localPosition;}
            return eye.parent.InverseTransformPoint(pivotWorld);
        }
        void Weight(int slot,double value)
        {int index=morphIndices[slot];if(index>=0)skin.SetBlendShapeWeight(index,(float)AttentionMath.Clamp(value,0,1)*100);}
        public void Restore()
        {
            if(!ready)return;
            if(neck!=null)neck.localRotation=neckRest;
            if(head!=null)head.localRotation=headRest;
            if(leftEye!=null){leftEye.localRotation=leftRest;leftEye.localPosition=leftPosition;}
            if(rightEye!=null){rightEye.localRotation=rightRest;rightEye.localPosition=rightPosition;}
            if(skin!=null)for(int i=0;i<morphIndices.Length;i++)if(morphIndices[i]>=0&&(i!=7||OwnBlink))skin.SetBlendShapeWeight(morphIndices[i],morphRest[i]);
            BlushWriter?.Invoke(0);ready=false;
        }
        void OnDisable()=>Restore();
    }
}
