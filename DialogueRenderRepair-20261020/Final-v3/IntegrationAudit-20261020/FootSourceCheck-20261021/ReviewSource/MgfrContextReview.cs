using System;
using System.IO;
using System.Collections;
using UnityEngine;
using MGFR.Wardrobe;
using MGFR.Dialogue;
namespace MGFR.StructuredVoiceFinal {
 public sealed class MgfrContextReview:MonoBehaviour {
  [Serializable] class Result {public bool pass,rayThigh,touchThigh,detached,equipped,packetsAccepted,noMicrophone;public int regions,acceptedPackets;public float maxSampleMs;public string mode="Actual current Unity runtime, bone regions, wardrobe callbacks and HTTP observations; synthetic voice backend; no headset";}
  IEnumerator Start(){
   AudioListener.volume=0;var args=Environment.GetCommandLineArgs();string output=args[Array.IndexOf(args,"-mgfr-context-review-out")+1];
   if(File.Exists(output))throw new InvalidOperationException("Review output already exists");
   float timeout=Time.realtimeSinceStartup+30;MgfrInteractionContext collector=null;WardrobeLiveRuntime wardrobe=null;
   while((collector=FindAnyObjectByType<MgfrInteractionContext>())==null||collector.RegionCount<10||(wardrobe=WardrobeLiveRuntime.Instance)==null||!wardrobe.IsReady){if(Time.realtimeSinceStartup>timeout){Application.Quit(3);yield break;}yield return null;}
   var result=new Result();result.regions=collector.RegionCount;
   var center=collector.RegionCenter("left_thigh");result.rayThigh=collector.LookAt(center+Vector3.forward*.5f,Vector3.back)=="left_thigh";
   result.touchThigh=collector.TouchAt(center,.008f,out _) == "left_thigh";
   var auto=FindAnyObjectByType<AutomaticVoiceSession>();result.noMicrophone=auto==null||!auto.CaptureRunning;
   collector.ReviewObserve("left_thigh");collector.ReviewObserve("left_arm",1);
   yield return new WaitForSecondsRealtime(1);
   result.detached=wardrobe.Adapter.TryDetach("shoe_left",out var piece,out _);
   yield return new WaitForSecondsRealtime(1.2f);
   int beforeEquip=collector.AcceptedPackets;result.equipped=wardrobe.Adapter.TryEquip("shoe_left",out _);
   float end=Time.realtimeSinceStartup+4;while(Time.realtimeSinceStartup<end&&(collector.AcceptedPackets<=beforeEquip||collector.QueuedEvents>0))yield return null;
   result.packetsAccepted=collector.AcceptedPackets>=3;result.acceptedPackets=collector.AcceptedPackets;result.maxSampleMs=collector.MaxSampleMs;
   result.pass=result.regions>=10&&result.rayThigh&&result.touchThigh&&result.detached&&result.equipped&&result.packetsAccepted&&result.noMicrophone;
   using(var stream=new FileStream(output,FileMode.CreateNew))using(var writer=new StreamWriter(stream))writer.Write(JsonUtility.ToJson(result,true));
   Debug.Log("MGFR_CONTEXT_REVIEW_"+(result.pass?"PASS":"FAIL"));Application.Quit(result.pass?0:4);
  }
 }
}
