using System;
using System.IO;
using System.Collections;
using UnityEngine;

namespace MGFR.Dialogue
{
 public sealed class ChatOverlayReview:MonoBehaviour
 {
  [Serializable]class Report{public bool pass,headLocked,streamUpdated,foregroundPreserved;public int roleGlyphQuads;public float angularWidth,angularHeight,whitePreservation;public string source="SYNTHETIC_TEXT_REAL_RENDER_NOT_HEADSET";}
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-chat-review")>=0)new GameObject("Chat overlay review").AddComponent<ChatOverlayReview>();}
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string dir=args[Array.IndexOf(args,"-mgfr-chat-dir")+1];Directory.CreateDirectory(dir);
   yield return new WaitForSecondsRealtime(1);
   var overlay=FindAnyObjectByType<CameraChatOverlay>();var camera=Camera.main;var report=new Report();
   overlay.ShowReview("今天有点累，陪我聊一会儿吧。","那就先坐");yield return null;
   var partial=Snapshot(camera,Path.Combine(dir,"chat-streaming.png"));Destroy(partial);
   overlay.ShowReview("今天有点累，陪我聊一会儿吧。","那就先坐下歇会儿。想说什么都行，我在这里听着呢。");yield return null;
   report.streamUpdated=overlay.DisplayedReply.EndsWith("听着呢。");
   var baseline=Snapshot(camera,Path.Combine(dir,"chat-visible.png"));
   var before=overlay.transform.position-camera.transform.position;
   var position=camera.transform.position;camera.transform.position+=new Vector3(.3f,.1f,-.2f);
   report.headLocked=Vector3.Distance(before,overlay.transform.position-camera.transform.position)<.00001f;
   camera.transform.position=position;
   var occluder=GameObject.CreatePrimitive(PrimitiveType.Quad);occluder.transform.SetParent(camera.transform,false);occluder.transform.localPosition=new Vector3(0,0,.35f);occluder.transform.localScale=Vector3.one*2;
   var material=new Material(Shader.Find("Unlit/Color"));material.color=new Color(.45f,.02f,.09f);occluder.GetComponent<MeshRenderer>().sharedMaterial=material;
   Destroy(baseline);occluder.transform.localPosition=new Vector3(0,0,2);occluder.transform.localScale=Vector3.one*10;
   yield return null;baseline=Snapshot(camera,Path.Combine(dir,"chat-depth-baseline.png"));
   occluder.transform.localPosition=new Vector3(0,0,.35f);occluder.transform.localScale=Vector3.one*2;
   yield return null;var covered=Snapshot(camera,Path.Combine(dir,"chat-in-front.png"));
   int expected=0,preserved=0;
   for(int y=0;y<baseline.height;y++)for(int x=0;x<baseline.width;x++)
   {
    var a=baseline.GetPixel(x,y);var b=covered.GetPixel(x,y);
    // The overlay is below the centre of the camera. Its opaque glyph cores
    // must survive even when an opaque surface covers the entire view.
    if(y<baseline.height*.48f&&x>baseline.width*.22f&&x<baseline.width*.78f&&a.r>.88f&&a.g>.88f&&a.b>.88f)
    {expected++;if(b.r>.88f&&b.g>.88f&&b.b>.88f)preserved++;}
   }
   report.whitePreservation=expected>0?(float)preserved/expected:0;report.foregroundPreserved=expected>100&&report.whitePreservation>.95f;
   report.angularWidth=overlay.AngularWidth;report.angularHeight=overlay.AngularHeight;
   report.roleGlyphQuads=overlay.RoleGlyphQuads;
   report.pass=report.roleGlyphQuads>=2&&report.streamUpdated&&report.headLocked&&report.foregroundPreserved&&report.angularWidth<30&&report.angularHeight<11;
   File.WriteAllText(Path.Combine(dir,"chat-review.json"),JsonUtility.ToJson(report,true));Debug.Log("[MGFR chat review] "+JsonUtility.ToJson(report));
   Destroy(baseline);Destroy(covered);Destroy(occluder);Destroy(material);Application.Quit(report.pass?0:1);
  }
  static Texture2D Snapshot(Camera camera,string path)
  {
   var target=new RenderTexture(1600,1000,24);var previous=camera.targetTexture;camera.targetTexture=target;camera.Render();RenderTexture.active=target;
   var image=new Texture2D(1600,1000,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1600,1000),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());RenderTexture.active=null;camera.targetTexture=previous;target.Release();Destroy(target);return image;
  }
 }
}
