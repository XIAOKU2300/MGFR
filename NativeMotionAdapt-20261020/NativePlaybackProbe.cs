using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Skins;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Attention;
namespace MGFR.StructuredVoiceFinal {
 public sealed class MainAvatarActions:MonoBehaviour {
  public static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-native-probe")>=0)new GameObject("Native standard animation probe").AddComponent<NativePlaybackProbe>();}
 }
 [DefaultExecutionOrder(2600)] public sealed class NativePlaybackProbe:MonoBehaviour {
  [Serializable] public class Phase {public string name;public int frames,spikes;public float maxSpeed,maxStep;public string worst;}
  [Serializable] public class Report {public bool pass;public string method="Unity Humanoid offline retarget -> target-local curves -> Unity Animation CrossFade";public Phase[] phases;}
  Animation animation;SiCharacterLoader loader;string output,baked;bool sampling;Phase phase;Transform[] bones;Quaternion[] previous;float last;
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-probe-out")+1];baked=args[Array.IndexOf(args,"-mgfr-baked")+1];Directory.CreateDirectory(output);
   AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   SiSkinSwitcher skins;float end=Time.realtimeSinceStartup+40;while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady){if(Time.realtimeSinceStartup>end){Application.Quit(2);yield break;}yield return null;}
   loader=skins.Loader;var idle=FindAnyObjectByType<IdleMotionPlayer>();if(idle!=null)idle.enabled=false;var leg=FindAnyObjectByType<LegPlantSolver>();if(leg!=null)leg.enabled=false;var face=FindAnyObjectByType<FaceAttentionController>();if(face!=null)face.AutoUpdate=false;
   // Remove the previous procedural idle's helper pose before the baked native clips own the body.
   for(int i=0;i<loader.Renderer.bones.Length;i++){var b=loader.Renderer.bones[i];b.localRotation=Quaternion.identity;var p=loader.Data.bones[i].localScaled;b.localPosition=new Vector3(p[0],p[1],p[2]);}
   animation=loader.gameObject.AddComponent<Animation>();animation.playAutomatically=false;animation.cullingType=AnimationCullingType.AlwaysAnimate;
   foreach(string id in new[]{"idle","wave","talk_hands","think","arms_crossed"})Load(id);
   animation.Play("idle");var tracked=new List<Transform>();var set=new HashSet<string>{"腰","上半身","上半身2","下半身","首","頭","左肩","右肩","左腕","右腕","左ひじ","右ひじ","左手首","右手首","左足","右足","左ひざ","右ひざ"};foreach(var b in loader.Renderer.bones)if(set.Contains(b.name))tracked.Add(b);bones=tracked.ToArray();previous=new Quaternion[bones.Length];
   QualitySettings.vSyncCount=0;Application.targetFrameRate=60;yield return new WaitForSeconds(.8f);
   var phases=new List<Phase>();
   foreach(string id in new[]{"idle","wave","talk_hands","think","arms_crossed","idle"}){
    phase=new Phase{name=id};phases.Add(phase);for(int i=0;i<bones.Length;i++)previous[i]=bones[i].localRotation;last=Time.unscaledTime;sampling=true;
    animation.CrossFade(id,.45f,PlayMode.StopSameLayer);yield return new WaitForSeconds(id=="idle"?1.2f:Mathf.Min(animation[id].length*.55f,2.5f));Snapshot(phases.Count+"-"+id);yield return new WaitForSeconds(id=="idle"?1.2f:animation[id].length-Mathf.Min(animation[id].length*.55f,2.5f)+.15f);sampling=false;
    Debug.Log("NATIVE_ANIMATION_PHASE "+id+" frames="+phase.frames+" spikes="+phase.spikes+" maxSpeed="+phase.maxSpeed+" bone="+phase.worst);
   }
   var result=new Report{pass=true,phases=phases.ToArray()};foreach(var p in phases)if(p.spikes>0)result.pass=false;
   using(var w=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))w.Write(JsonUtility.ToJson(result,true));Application.Quit(result.pass?0:5);
  }
  string PathFor(Transform b){string path=b.name;while(b.parent!=loader.transform){b=b.parent;if(b==null)throw new Exception("Bone root mismatch");path=b.name+"/"+path;}return path;}
  void Load(string name){using(var r=new BinaryReader(File.OpenRead(Path.Combine(baked,name+".hpose")))){
   if(r.ReadInt32()!=0x45535048)throw new Exception("Baked pose format");int count=r.ReadInt32(),frames=r.ReadInt32();float fps=r.ReadSingle();int[] ids=new int[count];for(int i=0;i<count;i++)ids[i]=r.ReadInt32();
   var keys=new Keyframe[count,7][];for(int i=0;i<count;i++)for(int c=0;c<7;c++)keys[i,c]=new Keyframe[frames];
   for(int f=0;f<frames;f++)for(int i=0;i<count;i++)for(int c=0;c<7;c++)keys[i,c][f]=new Keyframe(f/fps,r.ReadSingle());
   var clip=new AnimationClip{legacy=true,frameRate=fps,wrapMode=name=="idle"?WrapMode.Loop:WrapMode.ClampForever};string[] properties={"localPosition.x","localPosition.y","localPosition.z","localRotation.x","localRotation.y","localRotation.z","localRotation.w"};
   for(int i=0;i<count;i++)for(int c=0;c<7;c++)clip.SetCurve(PathFor(loader.Renderer.bones[ids[i]]),typeof(Transform),properties[c],new AnimationCurve(keys[i,c]));clip.EnsureQuaternionContinuity();animation.AddClip(clip,name);
  }}
  void LateUpdate(){if(!sampling)return;float dt=Time.unscaledTime-last;if(dt<=0)return;last=Time.unscaledTime;phase.frames++;
   for(int i=0;i<bones.Length;i++){float angle=Quaternion.Angle(previous[i],bones[i].localRotation),speed=angle/dt;if(speed>phase.maxSpeed){phase.maxSpeed=speed;phase.worst=bones[i].name;}phase.maxStep=Mathf.Max(phase.maxStep,angle);if(!float.IsFinite(speed)||speed>600&&angle>3)phase.spikes++;previous[i]=bones[i].localRotation;}
  }
  void Snapshot(string name){var camera=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var old=camera.targetTexture;var pos=camera.transform.position;var rot=camera.transform.rotation;bool ortho=camera.orthographic;float size=camera.orthographicSize;
   var center=loader.transform.position+Vector3.up*.85f;camera.orthographic=true;camera.orthographicSize=1.05f;camera.transform.position=center+Vector3.back*3;camera.transform.LookAt(center);var rt=new RenderTexture(720,900,24);camera.targetTexture=rt;camera.Render();var active=RenderTexture.active;RenderTexture.active=rt;var image=new Texture2D(720,900,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,720,900),0,0);image.Apply();
   using(var f=new FileStream(Path.Combine(output,name+".png"),FileMode.CreateNew)){var bytes=image.EncodeToPNG();f.Write(bytes,0,bytes.Length);}RenderTexture.active=active;camera.targetTexture=old;camera.transform.SetPositionAndRotation(pos,rot);camera.orthographic=ortho;camera.orthographicSize=size;Destroy(image);rt.Release();Destroy(rt);
  }
 }
}
