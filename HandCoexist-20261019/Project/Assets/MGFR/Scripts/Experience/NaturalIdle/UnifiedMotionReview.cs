using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Wardrobe;
using MGFR.Attention;
using MGFR.Dialogue;

namespace MGFR.Experience
{
    public sealed class UnifiedMotionReview:MonoBehaviour
    {
        [Serializable] sealed class Report
        {
            public bool pass,finite=true,fullWardrobe,shoePose,clothApi,chromaGuard,roomFixed;
            public string mode="DESKTOP_SIMULATED_RIG_60HZ_XPBD_RENDER_SAMPLES_NOT_HEADSET";
            public int actionKinds,frames,parts,authoredLowerKeys=NaturalLowerBody.AuthoredKeys;
            public float maxAnkleError,maxFootSpeed,maxPelvisSpeed,maxSolePenetration,maxRestingSoleGap;
            public float leftTravel,rightTravel,maxKneeDegrees,anchorDrift;
            public int[] actions;
        }
        WardrobeLiveRuntime live;ShoeFootPose foot;IdleMotionPlayer idle;LegPlantSolver legs;FaceAttentionController face;
        string folder;Report r=new Report();HashSet<int> seen=new HashSet<int>();
        int[][] shoeIds=new int[2][];float time;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-unified-review")>=0)
                new GameObject("Full feature and lower body verification").AddComponent<UnifiedMotionReview>();
        }
        IEnumerator Start()
        {
            var args=Environment.GetCommandLineArgs();folder=args[Array.IndexOf(args,"-mgfr-check-dir")+1];Directory.CreateDirectory(folder);
            float end=Time.realtimeSinceStartup+45;
            while((live=WardrobeLiveRuntime.Instance)==null||!live.IsReady)
            {if(Time.realtimeSinceStartup>end){Application.Quit(2);yield break;}yield return null;}
            yield return null;
            foot=ShoeFootPose.Instance;idle=FindAnyObjectByType<IdleMotionPlayer>();legs=FindAnyObjectByType<LegPlantSolver>();face=FindAnyObjectByType<FaceAttentionController>();
            r.parts=live.Adapter.Profile.parts.Length;r.fullWardrobe=r.parts==10;
            r.shoePose=foot.Ready;r.clothApi=live.Cloth.IsReady&&live.Cloth.Solver.EnabledGroups.Length==4;
            var guard=FindAnyObjectByType<MGFR.Rendering.MrChromaEdgeGuard>();r.chromaGuard=guard!=null&&guard.Requested;
            foreach(int side in new[]{0,1})
            {
                var part=live.Adapter.GetPart(side==0?"shoe_left":"shoe_right");
                var bytes=File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"wardrobe/with_shoes",part.indexFile));
                shoeIds[side]=new int[bytes.Length/4];Buffer.BlockCopy(bytes,0,shoeIds[side],0,bytes.Length);
            }
            live.Manual=true;foot.Manual=true;live.Cloth.Manual=true;idle.enabled=false;legs.enabled=false;face.AutoUpdate=false;
            live.Hands.enabled=false;live.Hands.Physics.enabled=false;
            live.Hands.Source.Replay=true;live.Hands.Source.SetReplayFrame(0,null,false);live.Hands.Source.SetReplayFrame(1,null,false);
            var captions=FindAnyObjectByType<CameraChatOverlay>();if(captions!=null)captions.SetVisible(false);
            var rig=live.Hands.Physics.Loader.Renderer.bones;var root=live.Hands.Physics.Loader.transform;
            var anchor=root.position;var first=new Vector3[2];var previous=new Vector3[2];Vector3 oldHips=Vector3.zero;
            for(int frame=0;frame<78*60;frame++)
            {
                time=frame/60f;const float dt=1f/60;
                idle.ReviewPlayback(false,0,time,dt);idle.Apply(time,dt);foot.Tick(dt);legs.SolveNow();face.Tick(time,dt);live.Hands.Physics.Tick(dt);
                if(frame%6==0)live.Cloth.Tick(dt);
                seen.Add(idle.LowerPose.Action);r.frames++;
                r.maxAnkleError=Mathf.Max(r.maxAnkleError,legs.AnkleError);r.anchorDrift=Mathf.Max(r.anchorDrift,Vector3.Distance(anchor,root.position));
                for(int side=0;side<2;side++)
                {
                    var goal=root.InverseTransformPoint(legs.Goals[side]);
                    if(frame==0){first[side]=goal;previous[side]=goal;}
                    float travel=Vector3.Distance(first[side],goal);if(side==0)r.leftTravel=Mathf.Max(r.leftTravel,travel);else r.rightTravel=Mathf.Max(r.rightTravel,travel);
                    if(frame>0)r.maxFootSpeed=Mathf.Max(r.maxFootSpeed,Vector3.Distance(previous[side],goal)/dt);previous[side]=goal;
                    r.maxKneeDegrees=Mathf.Max(r.maxKneeDegrees,Quaternion.Angle(Quaternion.identity,rig[side==0?22:26].localRotation));
                }
                if(frame>0)r.maxPelvisSpeed=Mathf.Max(r.maxPelvisSpeed,(idle.LowerPose.Hips-oldHips).magnitude/dt);oldHips=idle.LowerPose.Hips;
                foreach(var bone in rig)r.finite&=float.IsFinite(bone.position.sqrMagnitude)&&bone.localPosition.sqrMagnitude<100;
                if(frame%60==0)CheckSoles();
                int slot=frame/(13*60),within=frame%(13*60);
                if(within==4*60){Capture($"feet-action-{slot}.png",true);Capture($"body-action-{slot}.png",false);}
                if(frame%180==0)yield return null;
            }
            r.roomFixed=r.anchorDrift<.00001f;r.actionKinds=seen.Count;r.actions=new int[seen.Count];seen.CopyTo(r.actions);
            r.pass=r.finite&&r.fullWardrobe&&r.shoePose&&r.clothApi&&r.chromaGuard&&r.roomFixed&&r.actionKinds==6&&
                r.maxAnkleError<.005f&&r.maxFootSpeed<.2f&&r.leftTravel>.015f&&r.rightTravel>.015f&&r.maxSolePenetration<.012f&&r.maxRestingSoleGap<.015f;
            File.WriteAllText(Path.Combine(folder,"unified-motion.json"),JsonUtility.ToJson(r,true));
            Debug.Log("[Unified motion review] "+JsonUtility.ToJson(r));Application.Quit(r.pass?0:1);
        }
        void CheckSoles()
        {
            var renderer=live.Hands.Physics.Loader.Renderer;var mesh=new Mesh();renderer.BakeMesh(mesh);var vertices=mesh.vertices;
            for(int side=0;side<2;side++)
            {
                float lowest=float.PositiveInfinity;foreach(int i in shoeIds[side])lowest=Mathf.Min(lowest,vertices[i].y);
                r.maxSolePenetration=Mathf.Max(r.maxSolePenetration,-lowest);
                var delta=side==0?idle.LowerPose.Left:idle.LowerPose.Right;float pitch=side==0?idle.LowerPose.LeftPitch:idle.LowerPose.RightPitch;
                if(delta.y<.0001f&&Mathf.Abs(pitch)<.1f)r.maxRestingSoleGap=Mathf.Max(r.maxRestingSoleGap,lowest);
            }
            Destroy(mesh);
        }
        void Capture(string name,bool feet)
        {
            var root=live.Hands.Physics.Loader.transform;
            var camera=new GameObject("Unified pose capture").AddComponent<Camera>();camera.CopyFrom(Camera.main);camera.enabled=false;camera.stereoTargetEye=StereoTargetEyeMask.None;
            camera.transform.position=root.TransformPoint(feet?new Vector3(.56f,.24f,-.62f):new Vector3(.28f,.95f,-2.4f));
            camera.transform.LookAt(root.TransformPoint(feet?new Vector3(0,.22f,0):new Vector3(0,.90f,0)));
            if(feet){camera.orthographic=true;camera.orthographicSize=.37f;}
            var target=new RenderTexture(720,900,24);camera.targetTexture=target;camera.Render();var old=RenderTexture.active;RenderTexture.active=target;
            var image=new Texture2D(720,900,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,720,900),0,0);image.Apply();RenderTexture.active=old;
            File.WriteAllBytes(Path.Combine(folder,name),image.EncodeToPNG());camera.targetTexture=null;target.Release();Destroy(target);Destroy(image);Destroy(camera.gameObject);
        }
    }
}
