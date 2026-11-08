using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.BareHands;
using MGFR.Experience;
using UnityEngine;

namespace MGFR.Wardrobe
{
    public sealed class ShoeReview:MonoBehaviour
    {
        WardrobeLiveRuntime live;ShoeFootPose foot;LegPlantSolver legs;IdleMotionPlayer idle;
        Vector3 last;readonly List<string> report=new List<string>();string output;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-shoe-review")>=0)new GameObject("Shoe short replay").AddComponent<ShoeReview>();}
        static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        IEnumerator Start()
        {
            string[] args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-shoe-check")+1];Directory.CreateDirectory(Path.GetDirectoryName(output));
            float end=Time.realtimeSinceStartup+60;
            while((live=WardrobeLiveRuntime.Instance)==null||!live.IsReady)
            {if(Time.realtimeSinceStartup>end){Finish(false,"timeout");yield break;}yield return null;}
            yield return null;
            foot=ShoeFootPose.Instance;legs=FindAnyObjectByType<LegPlantSolver>();idle=FindAnyObjectByType<IdleMotionPlayer>();
            live.Manual=true;live.Cloth.Manual=true;foot.Manual=true;idle.enabled=false;legs.enabled=false;live.Hands.enabled=false;live.Hands.Physics.enabled=false;
            try{Run();Finish(true,"");}catch(Exception e){Finish(false,e.ToString());}
        }
        Pose[] Frame(Vector3 p,bool closed)
        {
            var a=new Pose[26];for(int i=0;i<26;i++)a[i]=new Pose(p+Vector3.forward*.06f,Quaternion.identity);
            a[1].position=p+Vector3.forward*.1f;a[12].position=p+new Vector3(.04f,0,.03f);
            a[5].position=p-Vector3.right*(closed?.009f:.045f);a[10].position=p+Vector3.right*(closed?.009f:.045f);return a;
        }
        void Pump(Vector3 p,bool closed)
        {
            last=p;const float dt=1f/60;idle.Apply(.9f,dt);foot.Tick(dt);legs.SolveNow();
            live.Hands.Source.SetReplayFrame(0,Frame(p,closed),true);live.Hands.Source.SetReplayFrame(1,Frame(p,false),false);
            live.Hands.StepInteraction(dt);live.Step(dt);live.Cloth.Tick(dt);live.Hands.AcquireAfterPhysics();
            Check(!live.OwnsHand(0)||live.Hands.GrabbedBody[0]<0,"hand ownership conflict");
        }
        void Move(Vector3 p,bool closed,int steps=16)
        {Vector3 a=last;for(int i=1;i<=steps;i++)Pump(Vector3.Lerp(a,p,i/(float)steps),closed);}
        void Detach(string id)
        {
            Move(live.Socket(id),false);for(int i=0;i<3;i++)Pump(live.Socket(id),false);
            Vector3 socket=live.Socket(id);for(int i=0;i<3;i++)Pump(socket,true);
            Check(live.Pending(0)==id,"acquire failed: "+id+" actual "+live.Pending(0));
            var part=live.Adapter.GetPart(id);var d=part.pullDirectionLocal;
            Vector3 direction=live.Hands.Physics.Loader.transform.TransformVector(new Vector3(d[0],d[1],d[2]));
            Move(socket+direction*part.pullDistanceMetres*1.5f,true,20);
            Check(live.Held(0)==id&&!live.IsEquipped(id),"detach failed "+id);
            for(int i=0;i<24;i++)Pump(last,true);
        }
        void Release(){for(int i=0;i<3;i++)Pump(last,false);}
        void Reequip(string id)
        {
            Move(live.DroppedGrip(id),false);for(int i=0;i<3;i++)Pump(last,false);
            for(int i=0;i<3;i++)Pump(last,true);Check(live.Held(0)==id,"pickup failed "+id);
            Move(live.Socket(id),true);for(int i=0;i<3;i++)Pump(live.Socket(id),false);
            Check(live.IsEquipped(id),"equip failed "+id);
            for(int i=0;i<24;i++)Pump(last,false);
        }
        void Capture(string name)
        {
            var loader=live.Hands.Physics.Loader;var root=loader.transform;
            var cam=new GameObject("shoe check camera").AddComponent<Camera>();cam.enabled=false;cam.stereoTargetEye=StereoTargetEyeMask.None;
            cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.16f,.18f,.2f);cam.nearClipPlane=.01f;cam.farClipPlane=10;cam.orthographic=true;cam.orthographicSize=.40f;
            cam.transform.position=root.TransformPoint(new Vector3(.62f,.23f,-.48f));cam.transform.LookAt(root.TransformPoint(new Vector3(0,.23f,0)));
            var rt=new RenderTexture(900,900,24){antiAliasing=4};cam.targetTexture=rt;
            cam.Render();var old=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(900,900,TextureFormat.RGB24,false);
            image.ReadPixels(new Rect(0,0,900,900),0,0);image.Apply();RenderTexture.active=old;
            string path=Path.Combine(Path.GetDirectoryName(output),name+".png");using(var f=new FileStream(path,FileMode.CreateNew)){byte[] b=image.EncodeToPNG();f.Write(b,0,b.Length);}
            cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(cam.gameObject);Destroy(image);
        }
        void Run()
        {
            report.Add("mode=PACKAGED_PLAYER_SYNTHETIC_HANDS_NOT_HEADSET");
            last=live.Socket("shoe_left");for(int i=0;i<24;i++)Pump(last,false);
            Check(live.Adapter.Profile.parts.Length==10,"not ten parts");Capture("01-both-on");
            foreach(string id in new[]{"shoe_left","shoe_right"})
            {
                int side=id=="shoe_left"?0:1;Detach(id);
                Check(foot.Weights[side]<.001f&&foot.Weights[1-side]>.999f,"foot poses not independent");
                report.Add(id+" independentOff=PASS heelWeight="+foot.Weights[side]);
                if(side==0)Capture("02-one-off");Release();Reequip(id);
                Check(foot.Weights[side]>.999f,"shoe pose not restored");
                report.Add(id+" pull/drop/pickup/equip=PASS");
            }
            Detach("shoe_left");Release();Detach("shoe_right");Release();
            for(int i=0;i<24;i++)Pump(last,false);
            Check(foot.Weights[0]<.001f&&foot.Weights[1]<.001f&&foot.AppliedBodyLift<.0001f,"both barefoot not restored");
            Capture("03-both-off");report.Add("bothBarefootAndHeightRestored=PASS");
            live.ResetAll();for(int i=0;i<30;i++)Pump(last,false);
            Check(live.IsEquipped("shoe_left")&&live.IsEquipped("shoe_right")&&foot.Weights[0]>.999f&&foot.Weights[1]>.999f,"reset failed");
            report.Add("reset=PASS");report.Add("renderMorphs="+live.Hands.Physics.Loader.Renderer.sharedMesh.blendShapeCount);
        }
        void Finish(bool pass,string error)
        {
            if(error.Length>0)report.Add("error="+error);report.Add("pass="+pass);
            using(var f=new FileStream(output,FileMode.CreateNew))using(var w=new StreamWriter(f))foreach(var line in report)w.WriteLine(line);
            Debug.Log("[Shoe replay] "+string.Join(" | ",report));Application.Quit(pass?0:1);
        }
    }
}
