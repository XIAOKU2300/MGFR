using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.BareHands;
using MGFR.Experience;
using MGFR.Skins;
using UnityEngine;

namespace MGFR.Wardrobe
{
    public sealed class WardrobeLiveReview : MonoBehaviour
    {
        readonly List<string> report=new List<string>();
        WardrobeLiveRuntime live;Vector3 last;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-wardrobe-review")>=0)new GameObject("Wardrobe live replay check").AddComponent<WardrobeLiveReview>();}
        static void Check(bool value,string label){if(!value)throw new InvalidOperationException(label);}
        IEnumerator Start()
        {
            report.Add("mode=REAL_PLAYER_WITH_SYNTHETIC_HAND_REPLAY_NOT_HEADSET");
            float end=Time.realtimeSinceStartup+60;
            while((live=WardrobeLiveRuntime.Instance)==null||!live.IsReady)
            {
                if(Time.realtimeSinceStartup>end){Finish(false,"initialization timeout");yield break;}
                yield return null;
            }
            yield return null;
            live.Manual=true;live.Cloth.Manual=true;live.Hands.enabled=false;live.Hands.Physics.enabled=false;
            var idle=FindAnyObjectByType<IdleMotionPlayer>();if(idle!=null)idle.enabled=false;
            try {Run();Finish(true,"");}catch(Exception e){Finish(false,e.ToString());}
        }
        Pose[] Frame(Vector3 point,bool closed)
        {
            var poses=new Pose[26];for(int i=0;i<26;i++)poses[i]=new Pose(point+Vector3.forward*.06f,Quaternion.identity);
            poses[0].position=point+Vector3.forward*.06f;poses[1].position=point+Vector3.forward*.10f;
            poses[12].position=point+new Vector3(.04f,0,.03f);
            float spread=closed?.009f:.045f;
            poses[5].position=point-Vector3.right*spread;poses[10].position=point+Vector3.right*spread;
            return poses;
        }
        void Pump(Vector3 point,bool closed,bool tracked=true)
        {
            last=point;live.Hands.Source.SetReplayFrame(0,Frame(point,closed),tracked);
            live.Hands.Source.SetReplayFrame(1,Frame(point,false),false);
            const float dt=1f/60;
            live.Hands.StepInteraction(dt);live.Step(dt);live.Cloth.Tick(dt);live.Hands.AcquireAfterPhysics();
            Check(!live.OwnsHand(0)||live.Hands.GrabbedBody[0]<0,"legacy hand grab overlaps wardrobe");
        }
        void OpenAt(Vector3 target)
        {
            Vector3 start=last;for(int i=1;i<=10;i++)Pump(Vector3.Lerp(start,target,i/10f),false);
            for(int i=0;i<3;i++)Pump(target,false);
        }
        void MoveHeld(Vector3 target)
        {Vector3 start=last;for(int i=1;i<=16;i++)Pump(Vector3.Lerp(start,target,i/16f),true);}
        void Detach(string id)
        {
            var part=live.Adapter.GetPart(id);Vector3 socket=live.Socket(id);
            OpenAt(socket);for(int i=0;i<3;i++)Pump(socket,true);
            Check(live.Pending(0)==id,"did not acquire "+id+"; actual="+live.Pending(0));
            Vector3 direction=new Vector3(part.pullDirectionLocal[0],part.pullDirectionLocal[1],part.pullDirectionLocal[2]);
            var root=live.Hands.Physics.Loader.transform;
            for(int i=1;i<=16;i++)Pump(socket+root.TransformVector(direction*(part.pullDistanceMetres*1.3f*i/16)),true);
            Check(!live.IsEquipped(id)&&live.Held(0)==id,"did not detach "+id);
        }
        void Run()
        {
            live.Hands.Source.Replay=true;last=live.Socket("cover_skirt");
            int initial=live.Cloth.VisibleClothTriangles;
            foreach(string id in new[]{"cover_skirt","wrist_left"})
            {
                int before=live.DetachCount;var part=live.Adapter.GetPart(id);Detach(id);
                Check(live.DetachCount==before+1,"detach count");
                if(part.materialSlot==10)Check(live.Cloth.VisibleClothTriangles==initial-part.triangleCount,"cloth geometry not hidden");
                Pump(last,false);Pump(last,false);Pump(last,false);
                Check(live.Held(0)==null&&!live.IsEquipped(id),"drop unexpectedly equipped");
                OpenAt(live.DroppedGrip(id));for(int i=0;i<3;i++)Pump(last,true);
                Check(live.Held(0)==id,"dropped part not picked up");
                MoveHeld(live.Socket(id));Pump(live.Socket(id),false);Pump(live.Socket(id),false);Pump(live.Socket(id),false);
                Check(live.IsEquipped(id)&&live.Held(0)==null,"socket equip failed "+id);
                Check(live.Cloth.VisibleClothTriangles==initial,"cloth geometry not restored");
                report.Add(id+"=pinch,pull,hold,drop,pickup,socket_equip PASS");
            }
            // A closed hand approaching after tracking loss cannot acquire until opened.
            Detach("sleeve_left");int loss=live.LossCancels;
            Pump(last,true,false);Check(live.Held(0)==null&&live.LossCancels==loss+1,"tracking loss did not cancel");
            Vector3 dropped=live.DroppedGrip("sleeve_left");
            Vector3 from=last;for(int i=1;i<=12;i++)Pump(Vector3.Lerp(from,dropped,i/12f),true);
            Check(live.Held(0)==null,"tracking recovery acquired without open hand");
            live.ResetAll();live.Step(1f/60);live.Cloth.Tick(1f/60);
            Check(live.IsEquipped("sleeve_left")&&live.Cloth.VisibleClothTriangles==initial,"reset did not restore cloth");
            report.Add("trackingLossAndOpenToRearm=PASS");
            var skins=FindAnyObjectByType<SiSkinSwitcher>();
            skins.Style.SetActive(!skins.Style.Active);live.Step(1f/60);live.Cloth.Tick(1f/60);
            Check(live.IsReady&&live.Cloth.VisibleClothTriangles==initial,"style rebind failed");
            Check(skins.TrySelect("original"),"switch to original failed");live.Step(1f/60);live.Cloth.Tick(1f/60);
            Check(!live.IsReady,"wardrobe stayed bound to original skin");
            Check(skins.TrySelect("swimsuit"),"switch back failed");live.Step(1f/60);live.Cloth.Tick(1f/60);
            Check(live.IsReady&&live.IsEquipped("cover_skirt"),"wardrobe did not rebind after skin switch");
            report.Add("styleAndSkinRoundTrip=PASS");
            report.Add("legacyGrabOwnership=PASS");report.Add("detachCount="+live.DetachCount+" equipCount="+live.EquipCount);
            report.Add("headsetValidation=NOT_RUN");
        }
        void Finish(bool pass,string error)
        {
            if(error.Length>0)report.Add("error="+error);report.Add("pass="+pass);
            string[] args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-wardrobe-check");
            string path=at>=0?args[at+1]:Path.Combine(Application.persistentDataPath,"wardrobe-check.txt");
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            using(var f=new FileStream(path,FileMode.CreateNew))using(var writer=new StreamWriter(f))foreach(string line in report)writer.WriteLine(line);
            Debug.Log("[Wardrobe replay] "+string.Join(" | ",report));Application.Quit(pass?0:1);
        }
    }
}
