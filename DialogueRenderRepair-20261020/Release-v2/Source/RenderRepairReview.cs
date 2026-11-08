using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Skins;
using MGFR.StructuredVoiceFinal;
namespace MGFR.Repairs {
 public sealed class RenderRepairReview:MonoBehaviour {
  [Serializable]class Result {public bool pass;public int cases,changedMaterials,nonKeyMaxError,shaderErrors;public string source="Actual current player, two outfits and render styles, normal and RGB-key cameras; no ALVR or headset";}
  IEnumerator Start(){
   AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   var args=Environment.GetCommandLineArgs();string output=args[Array.IndexOf(args,"-mgfr-render-repair-out")+1];if(Directory.Exists(output))throw new Exception("Review output exists");Directory.CreateDirectory(output);
   float deadline=Time.realtimeSinceStartup+45;SiSkinSwitcher skins;MrClothCoverageRepair repair;MainAvatarActions driver;
   while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||(repair=FindAnyObjectByType<MrClothCoverageRepair>())==null||!repair.Ready||(driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready){if(Time.realtimeSinceStartup>deadline){Application.Quit(2);yield break;}yield return null;}
   driver.ReviewOverride=true;driver.ReviewSpeaking=false;
   foreach(var overlay in FindObjectsByType<CameraChatOverlay>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))foreach(var r in overlay.GetComponentsInChildren<Renderer>())r.enabled=false;
   var camera=new GameObject("Material repair validation camera").AddComponent<Camera>();camera.CopyFrom(Camera.main);camera.enabled=false;camera.stereoTargetEye=StereoTargetEyeMask.None;camera.clearFlags=CameraClearFlags.SolidColor;camera.allowMSAA=false;camera.allowHDR=false;camera.orthographic=true;camera.orthographicSize=1.0f;
   var rt=new RenderTexture(800,1000,24,RenderTextureFormat.ARGB32){antiAliasing=1};rt.Create();camera.targetTexture=rt;camera.aspect=.8f;
   var result=new Result();
   foreach(string skin in new[]{"swimsuit","original"}){
    if(!skins.TrySelect(skin))throw new Exception("Skin unavailable");yield return new WaitForSeconds(.6f);
    foreach(bool zmd in new[]{true,false}){
     skins.Style.SetActive(zmd);yield return new WaitForSeconds(.3f);repair.RefreshMaterials();
     var center=skins.Loader.transform.position+Vector3.up*.88f;camera.transform.position=center+Vector3.back*3;camera.transform.LookAt(center);
     var variants=new Dictionary<Material,Shader>();foreach(var r in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))foreach(var m in r.sharedMaterials)if(m!=null&&m.shader.name.EndsWith("/MrCoverage",StringComparison.Ordinal)&&!variants.ContainsKey(m))variants.Add(m,m.shader);
     string prefix=skin+(zmd?"-zmd":"-current");result.changedMaterials+=variants.Count;
     camera.backgroundColor=Color.green;Original(variants);Save(camera,rt,output,prefix+"-before.png");Repaired(variants);Save(camera,rt,output,prefix+"-after.png");
     // Keep only the actual transparent cloth surface for a contamination comparison.
     var enabled=new Dictionary<Renderer,bool>();foreach(var r in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude,FindObjectsSortMode.None)){enabled[r]=r.enabled;r.enabled=r.name=="Simulated swimsuit cloth";}
     if(skin=="swimsuit"){Original(variants);Save(camera,rt,output,prefix+"-cloth-before.png");Repaired(variants);Save(camera,rt,output,prefix+"-cloth-after.png");}
     foreach(var pair in enabled)if(pair.Key!=null)pair.Key.enabled=pair.Value;
     camera.backgroundColor=new Color(.09f,.105f,.12f);Original(variants);var a=Capture(camera,rt);Repaired(variants);var b=Capture(camera,rt);for(int i=0;i<a.Length;i++)result.nonKeyMaxError=Mathf.Max(result.nonKeyMaxError,Mathf.Abs(a[i].r-b[i].r),Mathf.Abs(a[i].g-b[i].g),Mathf.Abs(a[i].b-b[i].b));
     foreach(var pair in variants)if(!pair.Value.isSupported)result.shaderErrors++;result.cases++;
    }
   }
   result.pass=result.cases==4&&result.changedMaterials>=4&&result.nonKeyMaxError<=1&&result.shaderErrors==0;
   using(var stream=new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew))using(var w=new StreamWriter(stream))w.Write(JsonUtility.ToJson(result,true));
   Debug.Log("MGFR_RENDER_REPAIR_REVIEW_"+(result.pass?"PASS":"FAIL"));Application.Quit(result.pass?0:5);
  }
  static void Original(Dictionary<Material,Shader> variants){foreach(var pair in variants){int queue=pair.Key.renderQueue;pair.Key.shader=Shader.Find(pair.Value.name.Substring(0,pair.Value.name.Length-"/MrCoverage".Length));pair.Key.renderQueue=queue;}}
  static void Repaired(Dictionary<Material,Shader> variants){foreach(var pair in variants){int queue=pair.Key.renderQueue;pair.Key.shader=pair.Value;pair.Key.renderQueue=queue;}}
  static Color32[] Capture(Camera camera,RenderTexture rt){camera.Render();var old=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();var pixels=image.GetPixels32();Destroy(image);RenderTexture.active=old;return pixels;}
  static void Save(Camera camera,RenderTexture rt,string output,string name){camera.Render();var old=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();using(var f=new FileStream(Path.Combine(output,name),FileMode.CreateNew)){var bytes=image.EncodeToPNG();f.Write(bytes,0,bytes.Length);}Destroy(image);RenderTexture.active=old;}
 }
}
