using System;
using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Character;
using MGFR.PhysicsRig;
using MGFR.Skins;

namespace MGFR.Experience
{
    [DefaultExecutionOrder(32050)]
    public sealed class NaturalIdleReview : MonoBehaviour
    {
        [Serializable] sealed class Report
        {
            public bool pass,finite=true,originalReady,swimsuitReady,returnedToOriginal;
            public int frames,authoredKeys=NaturalIdlePose.AuthoredKeys,captures;
            public float seconds,anchorDrift,maxAnkleError,maxIdleCpuMs,meanIdleCpuMs,maxPhysicsCpuMs;
            public float maxChestSpeedDeg,maxWristSpeedDeg,chestTravelDeg,wristTravelM,hairTipTravelM;
            public float breathMinimum=10,breathMaximum=-10,maxCurveSpeedDeg,maxCurveAcceleration;
            public float maxLegacyPeriodDifferenceDeg,meanFrameMs;
            public string mode="DESKTOP_AUTOMATED_NO_HEADSET_NO_REAL_HANDS_NO_VOICE";
        }
        IdleMotionPlayer idle;SiCharacterLoader loader;PmxSecondaryPhysics physics;SiSkinSwitcher skins;
        LegPlantSolver legs;Report report=new Report();Camera camera;RenderTexture rt;Texture2D image;
        string folder;float started,lastTime,nextCapture;bool ready,switched,returned;
        Vector3 anchor,firstWrist,firstHair;Quaternion firstChest,lastChest,lastWrist;
        int hairBone;bool haveFirst;float cpuSum;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-natural-idle-review")>=0)
                new GameObject("Natural idle bounded desktop review").AddComponent<NaturalIdleReview>();
        }
        IEnumerator Start()
        {
            var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,"-mgfr-check-dir");
            folder=args[i+1];Directory.CreateDirectory(folder);
            while((idle=FindAnyObjectByType<IdleMotionPlayer>())==null||
                  (physics=FindAnyObjectByType<PmxSecondaryPhysics>())==null||!physics.IsReady||
                  (skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady)yield return null;
            loader=idle.GetComponent<SiCharacterLoader>();legs=FindAnyObjectByType<LegPlantSolver>();
            yield return new WaitForSeconds(.8f);
            camera=new GameObject("Natural idle offscreen review camera").AddComponent<Camera>();
            camera.CopyFrom(Camera.main);camera.enabled=false;camera.stereoTargetEye=StereoTargetEyeMask.None;
            camera.transform.position=loader.transform.TransformPoint(new Vector3(.23f,1.0f,-2.45f));
            camera.transform.LookAt(loader.transform.TransformPoint(new Vector3(0,.91f,0)));
            rt=new RenderTexture(720,900,24,RenderTextureFormat.ARGB32);camera.targetTexture=rt;
            image=new Texture2D(720,900,TextureFormat.RGB24,false);
            anchor=loader.transform.position;firstWrist=loader.Renderer.bones[64].position;
            hairBone=Array.FindIndex(loader.Data.bones,b=>b.name=="L_hairE_jnt8");
            if(hairBone<0)hairBone=physics.Data.bodies[80].bone;
            firstHair=loader.transform.InverseTransformPoint(loader.Renderer.bones[hairBone].position);
            firstChest=loader.Renderer.bones[15].localRotation;
            CheckCurves();report.originalReady=skins.CurrentId=="original";
            started=lastTime=Time.unscaledTime;ready=true;
        }
        void CheckCurves()
        {
            var pose=idle.Natural;float dt=1f/144;
            var previous=new Vector3[6];var speeds=new float[6];int[] bones={12,13,14,15,32,64};
            for(int f=0;f<144*90;f++)
            {
                float t=f*dt,b=pose.Breath(t);
                report.finite&=float.IsFinite(b);report.breathMinimum=Mathf.Min(report.breathMinimum,b);report.breathMaximum=Mathf.Max(report.breathMaximum,b);
                for(int k=0;k<bones.Length;k++)
                {
                    var a=pose.Angles(bones[k],t);report.finite&=float.IsFinite(a.sqrMagnitude);
                    if(f>0)
                    {
                        float speed=(a-previous[k]).magnitude/dt;
                        report.maxCurveSpeedDeg=Mathf.Max(report.maxCurveSpeedDeg,speed);
                        if(f>1)report.maxCurveAcceleration=Mathf.Max(report.maxCurveAcceleration,Mathf.Abs(speed-speeds[k])/dt);
                        speeds[k]=speed;
                    }
                    previous[k]=a;
                    report.maxLegacyPeriodDifferenceDeg=Mathf.Max(report.maxLegacyPeriodDifferenceDeg,
                        (a-pose.Angles(bones[k],t+idle.Duration)).magnitude);
                }
            }
        }
        void LateUpdate()
        {
            if(!ready)return;
            float now=Time.unscaledTime,t=now-started,dt=now-lastTime;lastTime=now;
            report.frames++;report.seconds=t;report.meanFrameMs+=dt*1000;
            report.anchorDrift=Mathf.Max(report.anchorDrift,Vector3.Distance(anchor,loader.transform.position));
            report.maxAnkleError=Mathf.Max(report.maxAnkleError,legs.AnkleError);
            report.maxPhysicsCpuMs=Mathf.Max(report.maxPhysicsCpuMs,physics.LastMilliseconds);
            report.maxIdleCpuMs=Mathf.Max(report.maxIdleCpuMs,idle.LastNaturalMilliseconds);cpuSum+=idle.LastNaturalMilliseconds;
            var rig=loader.Renderer.bones;var chest=rig[15].localRotation;var wrist=rig[64].localRotation;
            if(haveFirst&&dt>.0001f&&dt<.10f&&!(t>13.8f&&t<15.5f)&&!(t>25.8f&&t<27.5f))
            {
                report.maxChestSpeedDeg=Mathf.Max(report.maxChestSpeedDeg,Quaternion.Angle(lastChest,chest)/dt);
                report.maxWristSpeedDeg=Mathf.Max(report.maxWristSpeedDeg,Quaternion.Angle(lastWrist,wrist)/dt);
            }
            haveFirst=true;lastChest=chest;lastWrist=wrist;
            if(!switched)
            {
                report.chestTravelDeg=Mathf.Max(report.chestTravelDeg,Quaternion.Angle(firstChest,chest));
                report.wristTravelM=Mathf.Max(report.wristTravelM,Vector3.Distance(firstWrist,rig[64].position));
                report.hairTipTravelM=Mathf.Max(report.hairTipTravelM,Vector3.Distance(firstHair,loader.transform.InverseTransformPoint(rig[hairBone].position)));
            }
            foreach(var bone in rig)report.finite&=float.IsFinite(bone.position.sqrMagnitude)&&bone.localPosition.sqrMagnitude<100;
            if(t>=nextCapture&&t<12)
            {Snapshot($"original-{report.captures:000}.png");report.captures++;nextCapture=t+.125f;}
            if(t>=14&&!switched)
            {switched=true;report.swimsuitReady=skins.TrySelect("swimsuit")&&skins.CurrentId=="swimsuit";nextCapture=15;}
            if(switched&&!returned&&t>=nextCapture&&t>=15&&t<20)
            {Snapshot($"swimsuit-{report.captures:000}.png");report.captures++;nextCapture=t+.25f;}
            if(t>=26&&!returned)
            {returned=true;report.returnedToOriginal=skins.TrySelect("original")&&skins.CurrentId=="original";}
            if(t<29)return;
            report.meanIdleCpuMs=cpuSum/Mathf.Max(1,report.frames);report.meanFrameMs/=Mathf.Max(1,report.frames);
            report.pass=report.finite&&report.anchorDrift<.00001f&&report.maxAnkleError<.01f&&
                report.chestTravelDeg>.25f&&report.wristTravelM>.001f&&report.hairTipTravelM>.0003f&&
                report.maxCurveSpeedDeg<12&&report.breathMaximum>.8f&&report.maxLegacyPeriodDifferenceDeg>.4f&&
                report.originalReady&&report.swimsuitReady&&report.returnedToOriginal;
            File.WriteAllText(Path.Combine(folder,"natural-idle-report.json"),JsonUtility.ToJson(report,true));
            Debug.Log("[Natural idle review] "+JsonUtility.ToJson(report));
            ready=false;Application.Quit(report.pass?0:1);
        }
        void Snapshot(string name)
        {
            camera.Render();var previous=RenderTexture.active;RenderTexture.active=rt;
            image.ReadPixels(new Rect(0,0,720,900),0,0);image.Apply();RenderTexture.active=previous;
            File.WriteAllBytes(Path.Combine(folder,name),image.EncodeToPNG());
        }
    }
}
