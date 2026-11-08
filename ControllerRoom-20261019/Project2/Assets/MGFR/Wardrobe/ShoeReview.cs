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
            try{
                var controller=FindAnyObjectByType<MGFR.Character.SiCharacterController>();if(controller!=null)controller.enabled=false;
                live.Hands.Physics.Loader.transform.rotation=Quaternion.Euler(0,33,0);
                Run();Finish(true,"");}catch(Exception e){Finish(false,e.ToString());}
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
        void Detach(string id,int anchor=0,Vector3? localPull=null,bool earlyPinch=false)
        {
            var root=live.Hands.Physics.Loader.transform;
            bool shoe=id.StartsWith("shoe_");
            Vector3 offset=earlyPinch?root.TransformVector(Vector3.right*(id=="shoe_left"?.065f:-.065f)):Vector3.zero;
            Vector3 socket=live.Socket(id,anchor)+offset;
            if(earlyPinch)
            {
                Vector3 outside=live.Socket(id,anchor)+offset*2.5f;
                Move(outside,false);for(int i=0;i<3;i++)Pump(outside,false);
                for(int i=0;i<4;i++)Pump(outside,true);
                Check(live.Pending(0)==null,"shoe grabbed from too far away");
                Move(socket,true,6);
            }
            else {Move(socket,false);for(int i=0;i<3;i++)Pump(socket,false);}
            for(int i=0;i<3;i++)Pump(socket,true);
            Check(live.Pending(0)==id,"acquire failed: "+id+" actual "+live.Pending(0));
            var part=live.Adapter.GetPart(id);var d=part.pullDirectionLocal;
            Vector3 direction=root.TransformVector(localPull??new Vector3(d[0],d[1],d[2]));
            for(int i=0;i<8;i++)Pump(socket,true);
            Check(live.IsEquipped(id),"stationary pinch detached "+id);
            Move(socket+direction*part.pullDistanceMetres*1.5f,true,12);
            Check(live.Held(0)==id&&!live.IsEquipped(id),"detach failed "+id);
            for(int i=0;i<24;i++)Pump(last,true);
        }
        void Release(){for(int i=0;i<3;i++)Pump(last,false);}
        void Reequip(string id)
        {
            Move(live.DroppedAnchor(id,1),false);for(int i=0;i<3;i++)Pump(last,false);
            for(int i=0;i<3;i++)Pump(last,true);Check(live.Held(0)==id,"pickup failed "+id);
            Vector3 target=live.HeldSocket(0);Move(target,true);for(int i=0;i<3;i++)Pump(target,false);
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
            var renderer=loader.Renderer;var snapshot=new Mesh();renderer.BakeMesh(snapshot);
            var display=new GameObject("current baked shoe pose");display.transform.SetParent(renderer.transform,false);
            display.AddComponent<MeshFilter>().sharedMesh=snapshot;display.AddComponent<MeshRenderer>().sharedMaterials=renderer.sharedMaterials;
            renderer.enabled=false;cam.Render();renderer.enabled=true;display.SetActive(false);Destroy(display);Destroy(snapshot);
            var old=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(900,900,TextureFormat.RGB24,false);
            image.ReadPixels(new Rect(0,0,900,900),0,0);image.Apply();RenderTexture.active=old;
            string path=Path.Combine(Path.GetDirectoryName(output),name+".png");using(var f=new FileStream(path,FileMode.CreateNew)){byte[] b=image.EncodeToPNG();f.Write(b,0,b.Length);}
            cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(cam.gameObject);Destroy(image);
        }
        void CheckFeet(string label)
        {
            var renderer=live.Hands.Physics.Loader.Renderer;var mesh=new Mesh();renderer.BakeMesh(mesh);
            var posed=mesh.vertices;var rest=renderer.sharedMesh.vertices;int[] body=renderer.sharedMesh.GetTriangles(7);
            for(int side=0;side<2;side++)
            {
                string id=side==0?"shoe_left":"shoe_right";float min=float.PositiveInfinity;
                if(live.IsEquipped(id))
                {
                    byte[] bytes=File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"wardrobe/with_shoes",live.Adapter.GetPart(id).indexFile));
                    int[] ids=new int[bytes.Length/4];Buffer.BlockCopy(bytes,0,ids,0,bytes.Length);
                    foreach(int vertex in ids)min=Mathf.Min(min,posed[vertex].y);
                }
                else foreach(int vertex in body)
                    if(rest[vertex].y<.055f&&rest[vertex].x*(side==0?1:-1)>0)min=Mathf.Min(min,posed[vertex].y);
                var target=renderer.bones[side==0?7:10];
                float restAnkle=renderer.sharedMesh.bindposes[side==0?23:27].inverse.MultiplyPoint3x4(Vector3.zero).y;
                float animatedLift=renderer.transform.InverseTransformPoint(target.position).y-restAnkle;
                float contactError=min-animatedLift;
                report.Add(label+" "+id+" soleY="+min+" originalIdleFootLift="+animatedLift+" contactError="+contactError);
                Check(contactError>-.015f&&contactError<.025f,"foot contact relative to idle goal: "+label+" "+id+" "+contactError);
                Check(Quaternion.Angle(renderer.bones[side==0?23:27].rotation,renderer.transform.rotation)<.01f,"foot yaw does not follow placement");
            }
            Destroy(mesh);
        }
        void Run()
        {
            report.Add("mode=PACKAGED_PLAYER_SYNTHETIC_HANDS_NOT_HEADSET");
            last=live.Socket("shoe_left");for(int i=0;i<24;i++)Pump(last,false);
            Check(live.Adapter.Profile.parts.Length==10,"not ten parts");CheckFeet("both-on");
            foreach(string id in new[]{"shoe_left","shoe_right"})
            {
                int side=id=="shoe_left"?0:1;
                Detach(id,side==0?4:2,side==0?Vector3.right:Vector3.up,side==0);
                Check(foot.Weights[side]<.001f&&foot.Weights[1-side]>.999f,"foot poses not independent");
                CheckFeet("single-"+id);
                report.Add(id+" independentOff=PASS heelWeight="+foot.Weights[side]);
                Release();Check(!live.IsEquipped(id),"freshly detached shoe snapped back on release");Reequip(id);
                Check(foot.Weights[side]>.999f,"shoe pose not restored");
                report.Add(id+" pull/drop/pickup/equip=PASS");
            }
            // Toe and upper strap work with different pull directions too.
            Detach("shoe_left",1,Vector3.forward);Release();
            Detach("shoe_right",3,Vector3.back);Release();
            for(int i=0;i<24;i++)Pump(last,false);
            Check(foot.Weights[0]<.001f&&foot.Weights[1]<.001f&&foot.AppliedBodyLift<.0001f,"both barefoot not restored");
            CheckFeet("both-off");report.Add("bothBarefootAndHeightRestored=PASS");
            live.ResetAll();for(int i=0;i<30;i++)Pump(last,false);
            Check(live.IsEquipped("shoe_left")&&live.IsEquipped("shoe_right")&&foot.Weights[0]>.999f&&foot.Weights[1]>.999f,"reset failed");
            report.Add("reset=PASS");
            // A pinch held for a long time cannot acquire by drifting near a shoe.
            Vector3 far=live.Socket("shoe_left",4)+live.Hands.Physics.Loader.transform.right*.3f;
            Move(far,false);for(int i=0;i<30;i++)Pump(far,true);
            Move(live.Socket("shoe_left",4),true);Check(live.Pending(0)==null,"long pinch auto-acquired");
            Release();for(int i=0;i<3;i++)Pump(last,true);
            Check(live.Pending(0)=="shoe_left","open/close did not rearm");
            live.Hands.Source.SetReplayFrame(0,Frame(last,true),false);live.Step(1f/60);
            Check(!live.OwnsHand(0)&&live.IsEquipped("shoe_left"),"tracking loss detached shoe");
            for(int i=0;i<6;i++)Pump(last,true);
            Check(live.Pending(0)==null,"tracking recovery acquired without opening");Release();
            report.Add("multiAnchor/arbitraryPull/65mmReach/earlyPinch/stationaryHold/longPinch/trackingLoss=PASS");
            report.Add("renderMorphs="+live.Hands.Physics.Loader.Renderer.sharedMesh.blendShapeCount);
        }
        void Finish(bool pass,string error)
        {
            if(error.Length>0)report.Add("error="+error);report.Add("pass="+pass);
            using(var f=new FileStream(output,FileMode.CreateNew))using(var w=new StreamWriter(f))foreach(var line in report)w.WriteLine(line);
            Debug.Log("[Shoe replay] "+string.Join(" | ",report));Application.Quit(pass?0:1);
        }
    }
}
