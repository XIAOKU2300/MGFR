using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Experience;
using MGFR.Attention;

namespace MGFR.Rendering
{
 public sealed class RenderReview:MonoBehaviour
 {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(System.Array.IndexOf(System.Environment.GetCommandLineArgs(),"-mgfr-render-review")>=0)
    new GameObject("Render comparison").AddComponent<RenderReview>();
  }
  IEnumerator Start()
  {
   var args=System.Environment.GetCommandLineArgs();
   string directory=args[System.Array.IndexOf(args,"-mgfr-review-dir")+1];Directory.CreateDirectory(directory);
   SiStylizedRenderer style;
   while((style=FindAnyObjectByType<SiStylizedRenderer>())==null||!style.IsReady)yield return null;
   var idle=FindAnyObjectByType<IdleMotionPlayer>();idle.ManualTime=.9f;
   yield return null;yield return null;
   idle.enabled=false;FindAnyObjectByType<LegPlantSolver>().enabled=false;
   FindAnyObjectByType<FaceAttentionController>().AutoUpdate=false;
   FindAnyObjectByType<SkirtDynamics>().enabled=false;
   style.Loader.gameObject.layer=8;
   var camera=new GameObject("Comparison camera").AddComponent<Camera>();
   camera.CopyFrom(Camera.main);camera.enabled=false;camera.stereoTargetEye=StereoTargetEyeMask.None;camera.cullingMask=1<<8;
   var rt=new RenderTexture(1100,1100,24,RenderTextureFormat.ARGB32);rt.antiAliasing=4;camera.targetTexture=rt;
   var image=new Texture2D(1100,1100,TextureFormat.RGB24,false);
   Vector3[] eyes={new Vector3(0,.91f,-2.5f),new Vector3(0,1.51f,-.72f),new Vector3(.65f,1.51f,-.8f),new Vector3(0,1.0f,-1f),new Vector3(0,.95f,2.5f)};
   Vector3[] targets={Vector3.up*.9f,Vector3.up*1.49f,Vector3.up*1.49f,Vector3.up*.98f,Vector3.up*.9f};
   string[] names={"body","face","threequarter","cloth","back"};float[] fov={45,30,30,50,45};
   var key=FindAnyObjectByType<Light>();var originalRotation=key.transform.rotation;
   for(int lighting=0;lighting<3;lighting++)
   {
    key.transform.rotation=lighting==0?originalRotation:lighting==1?Quaternion.Euler(15,75,0):Quaternion.Euler(80,0,0);
    for(int pose=0;pose<(lighting==0?5:2);pose++)
    {
     camera.transform.position=style.Loader.transform.TransformPoint(eyes[pose]);
     camera.transform.LookAt(style.Loader.transform.TransformPoint(targets[pose]));camera.fieldOfView=fov[pose];
     for(int variant=0;variant<2;variant++)
     {
      style.SetStylized(variant==1);camera.Render();RenderTexture.active=rt;
      image.ReadPixels(new Rect(0,0,1100,1100),0,0);image.Apply();RenderTexture.active=null;
      string path=Path.Combine(directory,$"L{lighting}-{names[pose]}-{(variant==0?"before":"after")}.png");
      File.WriteAllBytes(path,image.EncodeToPNG());
     }
     yield return null;
    }
   }
   style.SetStylized(true);key.transform.rotation=originalRotation;
   bool alpha=style.Loader.Materials[10].renderQueue==3000&&style.Loader.Materials[10].GetFloat("_ZWrite")==0;
   bool tangents=style.Loader.Renderer.sharedMesh.tangents.Length==style.Loader.Data.counts.vertices;
   string report=$"transparentLayerPreserved={alpha}\ntangentsComplete={tangents}\nmaterials={style.Loader.Materials.Length}\n";
   File.WriteAllText(Path.Combine(directory,"review-checks.txt"),report);
   Debug.Log("[MGFR render review] "+report.Replace('\n',' '));
   camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(image);
   yield return new WaitForSeconds(.2f);Application.Quit(alpha&&tangents?0:1);
  }
 }
}
