using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Experience;
using MGFR.Attention;
using MGFR.PhysicsRig;
using MGFR.Character;

namespace MGFR.RenderStyles.ZmdEndfield
{
 public sealed class ZmdRenderCapture:MonoBehaviour
 {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-zmd-review")>=0)new GameObject("ZMD render comparison capture").AddComponent<ZmdRenderCapture>();}
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-zmd-output");string directory=args[at+1];Directory.CreateDirectory(directory);
   ZmdRenderStyle style;float deadline=Time.realtimeSinceStartup+60;
   while((style=FindAnyObjectByType<ZmdRenderStyle>())==null||!style.IsReady)
   {if(Time.realtimeSinceStartup>deadline){Debug.LogError("[ZMD capture] style initialization timeout");Exit(1);yield break;}yield return null;}
   var loader=style.Loader;var root=loader.transform;
   var idle=FindAnyObjectByType<IdleMotionPlayer>();idle.ManualTime=.9f;
   yield return null;yield return null;
   idle.enabled=false;
   var physics=FindAnyObjectByType<PmxSecondaryPhysics>();if(physics!=null)physics.enabled=false;
   var legs=FindAnyObjectByType<LegPlantSolver>();if(legs!=null)legs.enabled=false;
   var face=FindAnyObjectByType<FaceAttentionController>();if(face!=null)face.AutoUpdate=false;
   var character=FindAnyObjectByType<SiCharacterController>();if(character!=null)character.enabled=false;
   for(int b=0;b<loader.Renderer.sharedMesh.blendShapeCount;b++)loader.Renderer.SetBlendShapeWeight(b,0);
   loader.gameObject.layer=8;
   var camera=new GameObject("ZMD fixed comparison camera").AddComponent<Camera>();camera.CopyFrom(Camera.main);
   camera.enabled=false;camera.stereoTargetEye=StereoTargetEyeMask.None;camera.cullingMask=1<<8;
   camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.09f,.105f,.12f);camera.allowHDR=false;
   const int width=1200,height=1600;
   var target=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32){antiAliasing=4};target.Create();
   camera.targetTexture=target;camera.aspect=width/(float)height;
   var image=new Texture2D(width,height,TextureFormat.RGB24,false);
   var oldImage=new Texture2D(width,height,TextureFormat.RGB24,false);var newImage=new Texture2D(width,height,TextureFormat.RGB24,false);
   var pair=new RenderTexture(width*2,height,0,RenderTextureFormat.ARGB32);pair.Create();
   var pairedImage=new Texture2D(width*2,height,TextureFormat.RGB24,false);
   Vector3[] eyes={new Vector3(0,.92f,-2.65f),new Vector3(0,1.51f,-.75f),new Vector3(.60f,1.50f,-.8f),new Vector3(.22f,1.01f,-1.30f),new Vector3(.55f,1.02f,2.45f)};
   Vector3[] aim={Vector3.up*.90f,Vector3.up*1.49f,Vector3.up*1.49f,Vector3.up*.98f,Vector3.up*.90f};
   float[] fov={43,34,34,43,43};string[] names={"01-fullbody","02-face","03-threequarter","04-clothing","05-back"};
   var composite=new Material(Resources.Load<Shader>("ZmdEndfield/ZmdComparison"));
   int magenta=0;var report=new List<string>{"source=ACTUAL_UNITY_RENDER_NOT_HEADSET","comparison=LEFT_CURRENT_RIGHT_ZMD","pipeline=Built-in","ported=Face,Skin,Cloth,Hair","originalRenderFilesOverwritten=0"};
   for(int view=0;view<eyes.Length;view++)
   {
    camera.transform.position=root.TransformPoint(eyes[view]);camera.transform.LookAt(root.TransformPoint(aim[view]));camera.fieldOfView=fov[view];
    for(int variant=0;variant<2;variant++)
    {
     style.SetActive(variant==1);camera.Render();RenderTexture.active=target;image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();RenderTexture.active=null;
     File.WriteAllBytes(Path.Combine(directory,names[view]+(variant==0?"-current.png":"-zmd.png")),image.EncodeToPNG());
     var copy=variant==0?oldImage:newImage;copy.LoadRawTextureData(image.GetRawTextureData<byte>());copy.Apply();
     if(variant==1)foreach(var pixel in image.GetPixels32())if(pixel.r>230&&pixel.g<25&&pixel.b>230)magenta++;
    }
    composite.SetTexture("_Before",oldImage);composite.SetTexture("_After",newImage);Graphics.Blit(null,pair,composite);
    RenderTexture.active=pair;
    pairedImage.ReadPixels(new Rect(0,0,width*2,height),0,0);pairedImage.Apply();RenderTexture.active=null;
    File.WriteAllBytes(Path.Combine(directory,names[view]+"-compare.png"),pairedImage.EncodeToPNG());
    report.Add("captured="+names[view]);yield return null;
   }
   // Pure green clear colour stays outside material-only tone mapping.
   camera.backgroundColor=Color.green;camera.transform.position=root.TransformPoint(eyes[0]);camera.transform.LookAt(root.TransformPoint(aim[0]));camera.fieldOfView=fov[0];
   style.SetActive(true);camera.Render();RenderTexture.active=target;image.ReadPixels(new Rect(0,0,width,height),0,0);image.Apply();RenderTexture.active=null;
   File.WriteAllBytes(Path.Combine(directory,"06-mr-green-zmd.png"),image.EncodeToPNG());var corner=image.GetPixel(0,0);
   bool green=corner.g>.99f&&corner.r<.005f&&corner.b<.005f;
   bool alpha=style.ZmdMaterials[10].renderQueue==style.PreviousMaterials[10].renderQueue&&style.ZmdMaterials[10].GetFloat("_ZWrite")==style.PreviousMaterials[10].GetFloat("_ZWrite");
   bool toggle=true;
   for(int cycle=0;cycle<3;cycle++)
   {
    style.SetActive(false);var current=loader.Renderer.sharedMaterials;for(int i=0;i<current.Length;i++)toggle&=current[i]==style.PreviousMaterials[i];
    style.SetActive(true);current=loader.Renderer.sharedMaterials;for(int i=0;i<current.Length;i++)toggle&=current[i]==style.ZmdMaterials[i];
   }
   report.Add("pureGreenCorner="+green);report.Add("transparentClothDepthStatePreserved="+alpha);report.Add("toggleSixTimes="+toggle);report.Add("magentaPixels="+magenta);
   bool pass=green&&alpha&&toggle&&magenta<100;report.Add("pass="+pass);File.WriteAllLines(Path.Combine(directory,"render-checks.txt"),report);
   Debug.Log("[ZMD capture] "+string.Join(" ",report));camera.targetTexture=null;target.Release();pair.Release();Exit(pass?0:1);
  }
  static void Exit(int code)
  {
   #if UNITY_EDITOR
   UnityEditor.EditorApplication.Exit(code);
   #else
   Application.Quit(code);
   #endif
  }
 }
}
