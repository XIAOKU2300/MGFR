using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Skins;
using MGFR.Experience;
using MGFR.BareHands;

[DefaultExecutionOrder(2400)]
public sealed class SkinLiveReview : MonoBehaviour
{
    SiSkinSwitcher skins;
    int frame;
    string output;
    bool finished;
    readonly List<string> report = new List<string>{"source=LIVE_ANIMATION_IK_PHYSICS_DESKTOP_NOT_HEADSET"};
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Install()
    {
        if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-skin-live-review")>=0)
            new GameObject("Skin live integration review").AddComponent<SkinLiveReview>();
    }
    void Start()
    {
        var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-skin-output");
        output=args[at+1];Directory.CreateDirectory(output);
        Application.logMessageReceived+=OnLog;
        QualitySettings.vSyncCount=0;Application.targetFrameRate=72;
    }
    void Update()
    {
        if(finished)return;
        if(skins==null||!skins.IsReady){skins=FindAnyObjectByType<SiSkinSwitcher>();return;}
        if(frame==50||frame==150||frame==250)skins.TrySelect("original");
        if(frame==100||frame==200||frame==300)skins.TrySelect("swimsuit");
        if(frame==175||frame==225)skins.Style.SetActive(!skins.Style.Active);
    }
    void LateUpdate()
    {
        if(finished||skins==null||!skins.IsReady)return;
        foreach(var bone in skins.Loader.Renderer.bones)
            if(!float.IsFinite(bone.position.sqrMagnitude)){Finish(false,"nonfinite bone");return;}
        if(frame==90)Capture("10-live-original.png",false);
        if(frame==360)
        {
            var idle=skins.Loader.GetComponent<IdleMotionPlayer>();
            var legs=FindAnyObjectByType<LegPlantSolver>();var hands=FindAnyObjectByType<BareHandInteraction>();
            bool automatic=idle.enabled&&legs.enabled&&hands.Physics.enabled&&hands.enabled;
            report.Add("automaticAnimationIkPhysicsHands="+automatic);
            report.Add("ankleErrorMetres="+legs.AnkleError);
            report.Add("switchCount="+skins.SwitchCount);
            Capture("08-live-swimsuit.png",false);Capture("09-live-ankles.png",true);
            Finish(automatic&&skins.CurrentId=="swimsuit"&&skins.Style.Active,"");return;
        }
        frame++;
    }
    void Capture(string name,bool feet)
    {
        var root=skins.Loader.transform;
        var camera=new GameObject("Live skin capture").AddComponent<Camera>();camera.CopyFrom(Camera.main);camera.enabled=false;
        camera.stereoTargetEye=StereoTargetEyeMask.None;camera.cullingMask=1<<8;skins.Loader.gameObject.layer=8;
        camera.backgroundColor=new Color(.09f,.105f,.12f);camera.clearFlags=CameraClearFlags.SolidColor;camera.allowHDR=false;
        camera.transform.position=root.TransformPoint(feet?new Vector3(.65f,.15f,-.20f):new Vector3(0,.90f,-2.65f));
        camera.transform.LookAt(root.TransformPoint(feet?new Vector3(0,.10f,0):new Vector3(0,.87f,0)));
        camera.fieldOfView=feet?38:43;camera.aspect=1100f/1600;
        var target=new RenderTexture(1100,1600,24,RenderTextureFormat.ARGB32){antiAliasing=4};target.Create();camera.targetTexture=target;
        camera.Render();RenderTexture.active=target;var image=new Texture2D(1100,1600,TextureFormat.RGB24,false);
        image.ReadPixels(new Rect(0,0,1100,1600),0,0);image.Apply();RenderTexture.active=null;
        File.WriteAllBytes(Path.Combine(output,name),image.EncodeToPNG());camera.targetTexture=null;target.Release();
        Destroy(camera.gameObject);Destroy(image);Destroy(target);
    }
    void OnLog(string message,string trace,LogType type)
    {if(type==LogType.Error||type==LogType.Exception)Finish(false,message);}
    void Finish(bool pass,string error)
    {
        if(finished)return;finished=true;Application.logMessageReceived-=OnLog;
        if(error.Length>0)report.Add("error="+error);report.Add("pass="+pass);
        File.WriteAllLines(Path.Combine(output,"skin-live-checks.txt"),report);
        Debug.Log("[Skin live review] "+string.Join(" ",report));Application.Quit(pass?0:1);
    }
}
