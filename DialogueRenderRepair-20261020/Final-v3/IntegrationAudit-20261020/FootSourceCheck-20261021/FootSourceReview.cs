using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Skins;
using MGFR.Wardrobe;
namespace MGFR.StructuredVoiceFinal {
 [DefaultExecutionOrder(2900)] public sealed class FootSourceReview:MonoBehaviour {
  [Serializable] class Sample {public string version,skin,shoes,clip;public int frame;public float leftPitch,rightPitch,leftMinY,rightMinY;public bool finite;}
  [Serializable] class Report {public string mode="Actual packaged renderer and shoe morph; native file sampling, desktop only";public Sample[] samples;}
  SiSkinSwitcher skins;MainAvatarActions driver;string output;readonly List<Sample> rows=new List<Sample>();
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-foot-out")+1];Directory.CreateDirectory(output);
   AudioListener.volume=0;var voice=FindAnyObjectByType<AutomaticVoiceSession>();if(voice!=null)voice.enabled=false;
   float end=Time.realtimeSinceStartup+60;
   while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready||(skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||WardrobeLiveRuntime.Instance==null||!WardrobeLiveRuntime.Instance.IsReady||ShoeFootPose.Instance==null||!ShoeFootPose.Instance.Ready){if(Time.realtimeSinceStartup>end){Application.Quit(2);yield break;}yield return null;}
   driver.ReviewOverride=true;driver.enabled=false;skins.Loader.GetComponent<Animation>().enabled=false;
   var control=FindAnyObjectByType<SiCharacterController>();if(control!=null)control.enabled=false;
   var live=WardrobeLiveRuntime.Instance;live.Manual=true;live.Cloth.Manual=true;live.Hands.enabled=false;live.Hands.Physics.enabled=false;
   var foot=ShoeFootPose.Instance;foot.Manual=true;
   string root=Path.GetDirectoryName(output);
   foreach(string skin in new[]{"swimsuit","original"}){
    skins.TrySelect(skin);yield return null;yield return null;
    var renderer=skins.Loader.Renderer;
    foreach(string shoes in skin=="swimsuit"?new[]{"on","off"}:new[]{"original"}){
     if(shoes=="off")foreach(string id in new[]{"shoe_left","shoe_right"}){GameObject part;string reason;if(!live.Adapter.TryDetach(id,out part,out reason))throw new Exception(reason);part.SetActive(false);}
     foreach(string version in new[]{"before-update","current","native-source"}){
      string folder=version=="before-update"?Path.Combine(root,"../Applied-20261021-080203-071966/Backups/native-actions"):version=="current"?Path.Combine(root,"../../Player/MGFR_Data/StreamingAssets/native-actions"):Path.Combine(root,"native-source-feet");
      foreach(string clip in new[]{"idle","talk_hands","wave","walk"}){
       string path=Path.Combine(folder,skin,clip+".hpose");if(!File.Exists(path))continue;
       byte[] bytes=File.ReadAllBytes(path);int count=BitConverter.ToInt32(bytes,4),frames=BitConverter.ToInt32(bytes,8);int[] ids=new int[count];Buffer.BlockCopy(bytes,16,ids,0,count*4);
       foreach(int frame in new[]{0,frames/2,frames-1}){
        foot.UndoLift();var bones=renderer.bones;
        for(int i=0;i<bones.Length;i++){var p=skins.CurrentAppearance.Data.bones[i].localScaled;bones[i].localPosition=new Vector3(p[0],p[1],p[2]);bones[i].localRotation=Quaternion.identity;}
        for(int i=0;i<count;i++){int offset=16+4*count+(frame*count+i)*28;float[] v=new float[7];Buffer.BlockCopy(bytes,offset,v,0,28);bones[ids[i]].localPosition=new Vector3(v[0],v[1],v[2]);bones[ids[i]].localRotation=new Quaternion(v[3],v[4],v[5],v[6]);}
        for(int step=0;step<20;step++)foot.Tick(.05f);
        var row=new Sample{version=version,skin=skin,shoes=shoes,clip=clip,frame=frame,finite=true,leftMinY=float.PositiveInfinity,rightMinY=float.PositiveInfinity};
        Transform left=null,right=null;foreach(var b in bones){if(b.name=="左足首")left=b;if(b.name=="右足首")right=b;}
        row.leftPitch=Pitch(Quaternion.Inverse(skins.Loader.transform.rotation)*left.rotation);row.rightPitch=Pitch(Quaternion.Inverse(skins.Loader.transform.rotation)*right.rotation);
        var baked=new Mesh();renderer.BakeMesh(baked);var posed=baked.vertices;var rest=renderer.sharedMesh.vertices;
        for(int i=0;i<rest.Length;i++)if(rest[i].y<.08f){if(rest[i].x>0)row.leftMinY=Mathf.Min(row.leftMinY,posed[i].y);else row.rightMinY=Mathf.Min(row.rightMinY,posed[i].y);row.finite&=float.IsFinite(posed[i].x)&&float.IsFinite(posed[i].y)&&float.IsFinite(posed[i].z);}
        rows.Add(row);
        if(clip=="idle"&&frame==0){Capture(version+"-"+skin+"-"+shoes+"-side",new Vector3(1.3f,.19f,0),new Vector3(0,.19f,-.02f),.29f);Capture(version+"-"+skin+"-"+shoes+"-oblique",new Vector3(.8f,.28f,-.8f),new Vector3(0,.19f,-.02f),.29f);}
        Destroy(baked);
       }
      }
     }
    }
   }
   using(var writer=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))writer.Write(JsonUtility.ToJson(new Report{samples=rows.ToArray()},true));
   Debug.Log("FOOT_SOURCE_REVIEW_COMPLETE samples="+rows.Count);Application.Quit(0);
  }
  float Pitch(Quaternion q){Vector3 p=q*Vector3.back;return Mathf.Atan2(p.y,new Vector2(p.x,p.z).magnitude)*Mathf.Rad2Deg;}
  void Capture(string name,Vector3 position,Vector3 target,float size){
   var camera=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var root=skins.Loader.transform;var oldPos=camera.transform.position;var oldRot=camera.transform.rotation;var oldTarget=camera.targetTexture;bool oldOrtho=camera.orthographic;float oldSize=camera.orthographicSize;
   camera.orthographic=true;camera.orthographicSize=size;camera.transform.position=root.TransformPoint(position);camera.transform.LookAt(root.TransformPoint(target));
   var rt=new RenderTexture(960,720,24){antiAliasing=4};camera.targetTexture=rt;camera.Render();var old=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(960,720,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,960,720),0,0);image.Apply();using(var f=new FileStream(Path.Combine(output,name+".png"),FileMode.CreateNew)){var data=image.EncodeToPNG();f.Write(data,0,data.Length);}RenderTexture.active=old;camera.targetTexture=oldTarget;camera.transform.SetPositionAndRotation(oldPos,oldRot);camera.orthographic=oldOrtho;camera.orthographicSize=oldSize;Destroy(image);rt.Release();Destroy(rt);
  }
 }
}
