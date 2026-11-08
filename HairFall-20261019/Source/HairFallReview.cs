using System;
using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.PhysicsRig;
using MGFR.Skins;
using MGFR.Dialogue;

namespace MGFR.Experience
{
    [DefaultExecutionOrder(32050)]
    public sealed class HairFallReview : MonoBehaviour
    {
        [Serializable] sealed class Report
        {
            public string mode="DESKTOP_RENDERED_NO_HEADSET_NO_REAL_HANDS";
            public bool pass,finite=true,flexible,switched,returned;
            public int frames,flexibleLinks;
            public float leftHorizontalM,rightHorizontalM,leftDropM,rightDropM;
            public float maxHairSpeed,maxJointError,maxSkinSwitchJumpM,tipTravelOnTurnM,maxHairMs;
        }
        PmxSecondaryPhysics physics;SiSkinSwitcher skins;Report report=new Report();
        Camera proofCamera;RenderTexture target;Texture2D picture;string folder;
        int[] roots={86,103},tips={102,119};float start,nextShot;int shot;bool ready;
        Vector3[] previousTips=new Vector3[2],turnStart=new Vector3[2];
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-hair-review")>=0)
            {
                new GameObject("Long hair fall review").AddComponent<HairFallReview>();
                new GameObject("Hair head turn replay").AddComponent<HairHeadTurnReplay>();
            }
        }
        IEnumerator Start()
        {
            var args=Environment.GetCommandLineArgs();folder=args[Array.IndexOf(args,"-mgfr-check-dir")+1];Directory.CreateDirectory(folder);
            Application.targetFrameRate=72;QualitySettings.vSyncCount=0;
            while((physics=FindAnyObjectByType<PmxSecondaryPhysics>())==null||!physics.IsReady||
                  (skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady)yield return null;
            yield return new WaitForSeconds(.8f);
            var captions=FindAnyObjectByType<CameraChatOverlay>();if(captions!=null)captions.SetVisible(false);
            report.flexible=physics.FlexibleLongHair;
            foreach(var j in physics.Joints)if(j.name.Contains("hairE")&&j.angularYMotion!=ConfigurableJointMotion.Locked)report.flexibleLinks++;
            proofCamera=new GameObject("Hair diagnostic camera").AddComponent<Camera>();proofCamera.CopyFrom(Camera.main);
            proofCamera.enabled=false;proofCamera.stereoTargetEye=StereoTargetEyeMask.None;
            target=new RenderTexture(720,900,24);proofCamera.targetTexture=target;picture=new Texture2D(720,900,TextureFormat.RGB24,false);
            for(int i=0;i<2;i++)previousTips[i]=physics.Bodies[tips[i]].position;
            start=Time.unscaledTime;ready=true;
        }
        void LateUpdate()
        {
            if(!ready)return;float t=Time.unscaledTime-start;report.frames++;
            for(int s=0;s<2;s++)
            {
                var tip=physics.Bodies[tips[s]].position;
                if(t>12.9f&&t<13.2f||t>15.9f&&t<16.2f)
                    report.maxSkinSwitchJumpM=Mathf.Max(report.maxSkinSwitchJumpM,Vector3.Distance(tip,previousTips[s]));
                previousTips[s]=tip;
                if(t<5)turnStart[s]=tip;
                if(t>5&&t<11)report.tipTravelOnTurnM=Mathf.Max(report.tipTravelOnTurnM,Vector3.Distance(turnStart[s],tip));
                var diff=tip-physics.Bodies[roots[s]].position;
                if(t>11&&t<12)
                {
                    if(s==0){report.leftHorizontalM=new Vector2(diff.x,diff.z).magnitude;report.leftDropM=-diff.y;}
                    else {report.rightHorizontalM=new Vector2(diff.x,diff.z).magnitude;report.rightDropM=-diff.y;}
                }
            }
            for(int i=86;i<=119;i++)
            {
                var rb=physics.Bodies[i];report.finite&=float.IsFinite(rb.position.sqrMagnitude)&&rb.position.sqrMagnitude<25;
                if(t>2)report.maxHairSpeed=Mathf.Max(report.maxHairSpeed,rb.linearVelocity.magnitude);
            }
            if(t>2)foreach(var j in physics.Joints)if(j.name.Contains("hairE"))
                report.maxJointError=Mathf.Max(report.maxJointError,Vector3.Distance(j.transform.TransformPoint(j.anchor),j.connectedBody.transform.TransformPoint(j.connectedAnchor)));
            report.maxHairMs=Mathf.Max(report.maxHairMs,physics.LastMilliseconds);
            if(t>=nextShot&&t<12)
            {
                Snapshot($"side-{shot:000}.png",new Vector3(-2.3f,.98f,.45f));shot++;nextShot=t+.25f;
                if(shot==16||shot==44){Snapshot($"front-{shot:000}.png",new Vector3(.23f,.98f,-2.4f));Snapshot($"back-{shot:000}.png",new Vector3(.23f,.98f,2.4f));}
            }
            if(t>13&&!report.switched)
            {report.switched=skins.TrySelect("swimsuit");Snapshot("swimsuit-side.png",new Vector3(-2.3f,.98f,.45f));}
            if(t>16&&!report.returned)report.returned=skins.TrySelect("original");
            if(t<17)return;
            Snapshot("final-back.png",new Vector3(.23f,.98f,2.4f));
            report.pass=report.finite&&report.switched&&report.returned&&report.maxJointError<.02f&&report.maxHairSpeed<2.5f&&
                (!report.flexible||report.flexibleLinks==32&&report.leftHorizontalM<.30f&&report.rightHorizontalM<.30f&&report.leftDropM>.65f&&report.rightDropM>.65f)&&
                report.maxSkinSwitchJumpM<.08f;
            File.WriteAllText(Path.Combine(folder,"hair-fall-report.json"),JsonUtility.ToJson(report,true));
            Debug.Log("[Hair fall review] "+JsonUtility.ToJson(report));ready=false;Application.Quit(report.pass?0:1);
        }
        void Snapshot(string name,Vector3 point)
        {
            var actor=physics.Loader.transform;
            proofCamera.transform.position=actor.TransformPoint(point);proofCamera.transform.LookAt(actor.TransformPoint(new Vector3(0,.95f,.04f)));
            proofCamera.Render();var previous=RenderTexture.active;RenderTexture.active=target;
            picture.ReadPixels(new Rect(0,0,720,900),0,0);picture.Apply();RenderTexture.active=previous;
            File.WriteAllBytes(Path.Combine(folder,name),picture.EncodeToPNG());
        }
    }
    [DefaultExecutionOrder(850)]
    public sealed class HairHeadTurnReplay : MonoBehaviour
    {
        MGFR.Attention.FaceAttentionController face;float start=-1;
        void LateUpdate()
        {
            if(face==null){face=FindAnyObjectByType<MGFR.Attention.FaceAttentionController>();return;}
            if(start<0)start=Time.unscaledTime;
            float t=Time.unscaledTime-start;
            float w=Mathf.SmoothStep(0,1,Mathf.Clamp01((t-5)/1.4f))*(1-Mathf.SmoothStep(0,1,Mathf.Clamp01((t-9)/1.4f)));
            if(w>0)face.SubmitHeadGesture(new Vector3(0,w*10,0),Time.unscaledTime);
        }
    }
}
