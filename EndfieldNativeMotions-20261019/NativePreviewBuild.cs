using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
public static class NativePreviewBuild {
 static string Arg(string name){var a=Environment.GetCommandLineArgs();int i=Array.IndexOf(a,name);if(i<0||i+1>=a.Length)throw new Exception("Missing "+name);return a[i+1];}
 public static void Review(){
  try {
   string root=Arg("-nativeRoot"),output=Arg("-reviewOut");if(Directory.Exists(output))throw new Exception("Output exists");Directory.CreateDirectory(output);
   EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);QualitySettings.skinWeights=SkinWeights.FourBones;QualitySettings.antiAliasing=4;
   var player=new GameObject("Original Endfield Si").AddComponent<NativeMotionPlayer>();player.Build(Path.Combine(root,"assets-v1"),Path.Combine(root,"motions-v2"));player.Playing=false;
   var camera=new GameObject("Native review camera").AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;camera.orthographicSize=.92f;camera.nearClipPlane=.01f;camera.farClipPlane=50;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.19f,.22f,.25f);camera.transform.position=new Vector3(0,.82f,3.2f);camera.transform.LookAt(new Vector3(0,.82f,0));
   var rt=new RenderTexture(900,1100,24);rt.antiAliasing=4;camera.targetTexture=rt;var image=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);
   int[] clips={1,0,4,10,6};
   foreach(int clip in clips) {
    player.Load(clip);var data=player.Manifest.clips[clip];
    for(int pose=0;pose<3;pose++) {
     float t=data.duration*(pose+1)/4;player.Apply(t);camera.Render();RenderTexture.active=rt;image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();RenderTexture.active=null;
     string file=Path.Combine(output,clip.ToString("D2")+"-"+pose+".png");using(var f=new FileStream(file,FileMode.CreateNew)){var bytes=image.EncodeToPNG();f.Write(bytes,0,bytes.Length);}
    }
   }
   File.WriteAllText(Path.Combine(output,"review.txt"),"Original native model/Avatar. 16 source motion probes. Packed normals regenerated; simplified preview material. No runtime/humanoid foot IK equivalence claim.\n");
   Debug.Log("Native model review rendered: "+output);EditorApplication.Exit(0);
  } catch(Exception e){Debug.LogException(e);EditorApplication.Exit(1);}
 }
}
