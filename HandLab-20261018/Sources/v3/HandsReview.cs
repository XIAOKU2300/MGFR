using System;
using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Experience;
using MGFR.Attention;

namespace MGFR.BareHands
{
 public sealed class HandsReview:MonoBehaviour
 {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-hand-review")>=0)
    new GameObject("Bare hand integration review").AddComponent<HandsReview>();
  }
  static Pose[] PoseAt(Vector3 point,bool pinch,Quaternion rotation)
  {
   var local=new Vector3[26];local[0]=Vector3.zero;local[1]=new Vector3(0,-.05f,0);
   local[2]=new Vector3(-.035f,-.025f,0);local[3]=new Vector3(-.05f,0,0);local[4]=new Vector3(-.06f,.025f,0);local[5]=new Vector3(-.065f,.05f,0);
   for(int f=0;f<4;f++)for(int j=0;j<5;j++)local[6+f*5+j]=new Vector3(-.03f+f*.02f,.012f+j*.023f,0);
   if(pinch){local[5]=local[10]+new Vector3(-.009f,0,-.003f);local[4]=(local[3]+local[5])*.5f;}
   Vector3 offset=rotation*((local[5]+local[10])*.5f);
   var result=new Pose[26];for(int i=0;i<26;i++)result[i]=new Pose(point+rotation*local[i]-offset,rotation);
   return result;
  }
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string dir=args[Array.IndexOf(args,"-mgfr-hand-dir")+1];Directory.CreateDirectory(dir);
   BareHandInteraction hands;
   while((hands=FindAnyObjectByType<BareHandInteraction>())==null||!hands.IsReady)yield return null;
   var physics=hands.Physics;physics.enabled=false;var loader=physics.Loader;var root=loader.transform;
   var idle=loader.GetComponent<IdleMotionPlayer>();idle.enabled=false;idle.Apply(.9f);
   FindAnyObjectByType<LegPlantSolver>().enabled=false;loader.GetComponent<FaceAttentionController>().AutoUpdate=false;
   physics.ResetToAnimation();
   int target=Array.FindIndex(physics.Data.bodies,b=>b.name=="裙子_8_0");
   Vector3 point=root.TransformPoint(physics.Bodies[target].position);
   void Feed(int h,Vector3 p,bool pinch,bool tracked=true){hands.Source.SetReplayFrame(h,PoseAt(p,pinch,Quaternion.identity),tracked);}
   void Step(){hands.StepInteraction(1f/60f);physics.Tick(1f/60f);}
   Feed(0,point+Vector3.forward*.02f,false);Feed(1,point+Vector3.right*.15f,false);Step();
   bool both=hands.ActiveColliders==40;Feed(1,point,false,false);Step();bool oneLost=hands.ActiveColliders==20;
   point=root.TransformPoint(physics.Bodies[target].position);Feed(0,point,true);Step();
   bool clothGrab=hands.GrabbedBody[0]>=0;int grabbed=hands.GrabbedBody[0];
   Vector3 before=grabbed>=0?physics.Bodies[grabbed].position:Vector3.zero;
   for(int f=0;f<30;f++)
   {
    Feed(0,point+Vector3.back*(f/29f*.035f),true);Step();if(f%6==0)yield return null;
   }
   float clothMotion=grabbed>=0?Vector3.Distance(before,physics.Bodies[grabbed].position):0;
   Feed(0,point,true,false);Step();yield return null;
   bool lossRelease=hands.ActiveColliders==0&&hands.GrabbedBody[0]<0&&!hands.DepthMeshes[0].Object.activeSelf;
   var controllers=FindAnyObjectByType<ControllerHands>();Vector3 ball=controllers.Ball.position;
   Feed(0,ball,false);Step();Feed(0,ball,true);Step();bool ballGrab=controllers.Ball.isKinematic;
   Feed(0,ball,true,false);Step();bool ballReleased=!controllers.Ball.isKinematic;
   // Real model + identical camera/pose. Only depth-only hand geometry changes.
   hands.DebugHands=false;physics.enabled=false;loader.gameObject.layer=8;
   foreach(var mesh in hands.DepthMeshes)mesh.Object.layer=9;
   var camera=new GameObject("Hand occlusion review camera").AddComponent<Camera>();camera.CopyFrom(Camera.main);
   camera.enabled=false;camera.cullingMask=(1<<8)|(1<<9);camera.stereoTargetEye=StereoTargetEyeMask.None;camera.fieldOfView=42;
   var rt=new RenderTexture(900,900,24);rt.antiAliasing=4;camera.targetTexture=rt;
   var image=new Texture2D(900,900,TextureFormat.RGB24,false);int[] cuts=new int[2];int behindCuts=0;bool green=true;
   for(int eye=0;eye<2;eye++)
   {
    camera.transform.position=root.TransformPoint(new Vector3(eye==0?-.032f:.032f,1.1f,-1.8f));
    camera.transform.rotation=Quaternion.LookRotation(root.forward);camera.transform.Rotate(0,180,0,Space.World);
    // The model faces -Z; camera at -Z looks toward +Z in model space.
    camera.transform.rotation=root.rotation;
    byte[] Render(string name)
    {
     camera.Render();RenderTexture.active=rt;image.ReadPixels(new Rect(0,0,900,900),0,0);image.Apply();RenderTexture.active=null;
     File.WriteAllBytes(Path.Combine(dir,name),image.EncodeToPNG());return image.GetRawTextureData<byte>().ToArray();
    }
    int NewGreen(byte[] a,byte[] b)
    {
     int count=0;for(int p=0;p<a.Length;p+=3)if(b[p]==0&&b[p+1]==255&&b[p+2]==0&&(a[p]!=0||a[p+1]!=255||a[p+2]!=0))count++;return count;
    }
    Feed(0,root.TransformPoint(new Vector3(0,1.1f,-.48f)),false);hands.OcclusionEnabled=false;hands.StepInteraction(1f/60f);
    byte[] baseline=Render($"eye{eye}-without-hand-depth.png");
    hands.OcclusionEnabled=true;hands.StepInteraction(1f/60f);byte[] front=Render($"eye{eye}-hand-in-front.png");cuts[eye]=NewGreen(baseline,front);
    Feed(0,root.TransformPoint(new Vector3(0,1.1f,1.5f)),false);hands.StepInteraction(1f/60f);byte[] behind=Render($"eye{eye}-hand-behind.png");behindCuts+=NewGreen(baseline,behind);
    green&=front[0]==0&&front[1]==255&&front[2]==0;yield return null;
   }
   bool pass=both&&oneLost&&clothGrab&&clothMotion>.0001f&&lossRelease&&ballGrab&&ballReleased&&cuts[0]>200&&cuts[1]>200&&behindCuts<30&&green;
   string report=$"pass={pass}\nsource=TEST_REPLAY_NOT_HEADSET\nbothHands40Colliders={both}\noneHandLost20Colliders={oneLost}\nclothPinchGrab={clothGrab}\nclothMotionMetres={clothMotion}\ntrackingLossReleasesAndHides={lossRelease}\nballGrab={ballGrab}\nballReleaseOnTrackingLoss={ballReleased}\nleftEyeOccludedPixels={cuts[0]}\nrightEyeOccludedPixels={cuts[1]}\nbehindHandOccludedPixels={behindCuts}\ngreenCornerUnchanged={green}\nfingerContacts={hands.FingerContacts}\n";
   File.WriteAllText(Path.Combine(dir,"hands-review.txt"),report);Debug.Log("[MGFR hand review] "+report.Replace('\n',' '));
   camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(image);Application.Quit(pass?0:1);
  }
 }
}
