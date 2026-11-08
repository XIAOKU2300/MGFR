using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Skins;
using MGFR.Dialogue;
namespace MGFR.StructuredVoiceFinal {
 [Serializable] public class NNode {public string name;public int parent;public float[] t,q,s;}
 [Serializable] public class NRig {public NNode[] nodes;}
 [Serializable] public class NClip {public string name,file;public float duration,fps;public int frames;public bool loop;}
 [Serializable] public class NManifest {public NClip[] clips;}
 public sealed class MainAvatarActions:MonoBehaviour {
  public static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-avatar-bake")>=0)new GameObject("Native Humanoid bake").AddComponent<AvatarBake>();}
 }
 public sealed class AvatarBake:MonoBehaviour {
  sealed class Rig {public GameObject root;public Transform[] bones;public Dictionary<string,Transform> names;public Dictionary<string,string> human;public Avatar avatar;public HumanPoseHandler pose;public Vector3[] restPosition;public Quaternion[] restRotation;}
  string output,data;SiCharacterLoader loader;
  static Vector3 V(float[] p)=>new Vector3(p[0],p[1],p[2]);
  static Quaternion Q(float[] p)=>new Quaternion(p[0],p[1],p[2],p[3]);
  static Dictionary<string,string> Human(bool native){
   var map=new Dictionary<string,string>();
   string[] human={"Hips","Spine","Chest","UpperChest","Neck","Head","LeftShoulder","LeftUpperArm","LeftLowerArm","LeftHand","RightShoulder","RightUpperArm","RightLowerArm","RightHand","LeftUpperLeg","LeftLowerLeg","LeftFoot","LeftToes","RightUpperLeg","RightLowerLeg","RightFoot","RightToes"};
   string[] source={"Bip001_Pelvis","Bip001_Spine","Bip001_Spine1","Bip001_Spine2","Bip001_Neck","Bip001_Head","Bip001_L_Clavicle","Bip001_L_UpperArm","Bip001_L_Forearm","Bip001_L_Hand","Bip001_R_Clavicle","Bip001_R_UpperArm","Bip001_R_Forearm","Bip001_R_Hand","Bip001_L_Thigh","Bip001_L_Calf","Bip001_L_Foot","Bip001_L_Toe0","Bip001_R_Thigh","Bip001_R_Calf","Bip001_R_Foot","Bip001_R_Toe0"};
   string[] target={"腰","上半身","上半身1","上半身2","首","頭","左肩","左腕","左ひじ","左手首","右肩","右腕","右ひじ","右手首","左足","左ひざ","左足首","左つま先","右足","右ひざ","右足首","右つま先"};
   for(int i=0;i<human.Length;i++)map.Add(human[i],native?source[i]:target[i]);
   string[] fingers={"Thumb","Index","Middle","Ring","Little"},jp={"親指","人指","中指","薬指","小指"},part={"Proximal","Intermediate","Distal"};
   string[] digits={"０","１","２","３"};
   for(int side=0;side<2;side++)for(int f=0;f<5;f++)for(int j=0;j<3;j++){
    string h=(side==0?"Left":"Right")+fingers[f]+part[j];
    string n=native?"Bip001_"+(side==0?"L":"R")+"_Finger"+f+(j==0?"":j.ToString()):(side==0?"左":"右")+jp[f]+digits[f==0?j:j+1];map.Add(h,n);
   }
   return map;
  }
  Rig CreateSource(NRig data){
   var r=new Rig{root=new GameObject("SourceAvatar"),bones=new Transform[data.nodes.Length],names=new Dictionary<string,Transform>(),human=Human(true)};
   for(int i=0;i<r.bones.Length;i++){var n=data.nodes[i];var b=new GameObject(n.name).transform;b.SetParent(n.parent<0?r.root.transform:r.bones[n.parent],false);b.localPosition=V(n.t);b.localRotation=Q(n.q);b.localScale=V(n.s);r.bones[i]=b;r.names[n.name]=b;}
   return r;
  }
  Rig CreateTarget(){
   var r=new Rig{root=new GameObject("TargetAvatar"),bones=new Transform[loader.Data.bones.Length],names=new Dictionary<string,Transform>(),human=Human(false)};
   var facing=new GameObject("Facing").transform;facing.SetParent(r.root.transform,false);facing.localRotation=Quaternion.Euler(0,180,0);
   for(int i=0;i<r.bones.Length;i++)r.bones[i]=new GameObject(loader.Data.bones[i].name).transform;
   for(int i=0;i<r.bones.Length;i++){var n=loader.Data.bones[i];var b=r.bones[i];b.SetParent(n.parent<0?facing:r.bones[n.parent],false);b.localPosition=V(n.localScaled);b.localRotation=Quaternion.identity;r.names[n.name]=b;}
   return r;
  }
  void Calibrate(Rig r){
   foreach(string side in new[]{"Left","Right"}){
    var arm=r.names[r.human[side+"UpperArm"]];var elbow=r.names[r.human[side+"LowerArm"]];var hand=r.names[r.human[side+"Hand"]];
    var toward=(arm.position-r.names[r.human["UpperChest"]].position);var direction=Vector3.right*Mathf.Sign(toward.x);
    arm.rotation=Quaternion.FromToRotation(elbow.position-arm.position,direction)*arm.rotation;
    elbow.rotation=Quaternion.FromToRotation(hand.position-elbow.position,direction)*elbow.rotation;
   }
   var human=new List<HumanBone>();foreach(var pair in r.human){string unityName=pair.Key;int id=Array.IndexOf(Enum.GetNames(typeof(HumanBodyBones)),pair.Key);if(id<0)throw new Exception("Unknown human "+pair.Key);unityName=HumanTrait.BoneName[id];human.Add(new HumanBone{humanName=unityName,boneName=pair.Value,limit=new HumanLimit{useDefaultValues=true}});}
   var skeleton=new List<SkeletonBone>();foreach(var b in r.root.GetComponentsInChildren<Transform>(true))skeleton.Add(new SkeletonBone{name=b.name,position=b.localPosition,rotation=b.localRotation,scale=b.localScale});
   var description=new HumanDescription{human=human.ToArray(),skeleton=skeleton.ToArray(),upperArmTwist=.5f,lowerArmTwist=.5f,upperLegTwist=.5f,lowerLegTwist=.5f,armStretch=.05f,legStretch=.05f,feetSpacing=0,hasTranslationDoF=false};
   r.avatar=AvatarBuilder.BuildHumanAvatar(r.root,description);if(r.avatar==null||!r.avatar.isValid||!r.avatar.isHuman)throw new Exception("Invalid Humanoid Avatar: "+r.root.name);
   r.pose=new HumanPoseHandler(r.avatar,r.root.transform);r.restPosition=Array.ConvertAll(r.bones,b=>b.localPosition);r.restRotation=Array.ConvertAll(r.bones,b=>b.localRotation);
   Debug.Log("NATIVE_AVATAR_VALID "+r.root.name+" mapped="+human.Count+" scale="+r.avatar.humanDescription.human.Length);
  }
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-bake-out")+1];data=args[Array.IndexOf(args,"-mgfr-avatar-data")+1];Directory.CreateDirectory(output);
   var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;AudioListener.volume=0;
   SiSkinSwitcher skins;float deadline=Time.realtimeSinceStartup+40;
   while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady){if(Time.realtimeSinceStartup>deadline){Application.Quit(2);yield break;}yield return null;}
   loader=skins.Loader;
   try{string top=output;foreach(string skin in new[]{"swimsuit","original"}){if(!skins.TrySelect(skin))throw new Exception("Skin not available");loader=skins.Loader;output=Path.Combine(top,skin);Directory.CreateDirectory(output);Bake();}}catch(Exception e){Debug.LogException(e);Application.Quit(5);yield break;}Application.Quit(0);
  }
  void Bake(){
   var native=JsonUtility.FromJson<NRig>(File.ReadAllText(Path.Combine(data,"source-rig.json")));var manifest=JsonUtility.FromJson<NManifest>(File.ReadAllText(Path.Combine(data,"motions/manifest.json")));
   var source=CreateSource(native);var target=CreateTarget();Calibrate(source);Calibrate(target);
   // Save calibration evidence. Both avatars use the same official Humanoid muscle space.
   var report=new List<string>{"sourceAvatarValid="+source.avatar.isValid,"targetAvatarValid="+target.avatar.isValid,"muscles="+HumanTrait.MuscleCount,"bodyAndFingerMappings="+source.human.Count};
   var ids=new List<int>();for(int i=0;i<target.bones.Length;i++)if(target.human.ContainsValue(target.bones[i].name))ids.Add(i);
   foreach(int id in new[]{738,739,740,742,743,744})if(!ids.Contains(id))ids.Add(id);
   foreach(var clip in manifest.clips){

    var path=Path.Combine(output,clip.name+".hpose");
    using(var reader=new BinaryReader(File.OpenRead(Path.Combine(data,"motions",clip.file))))using(var writer=new BinaryWriter(new FileStream(path,FileMode.CreateNew))){
     reader.ReadBytes(8);int count=reader.ReadInt32(),frames=reader.ReadInt32();float rate=reader.ReadSingle();
     writer.Write(0x45535048);writer.Write(ids.Count);writer.Write(frames);writer.Write(rate);foreach(int id in ids)writer.Write(id);
     var pose=new HumanPose();Vector3 initial=Vector3.zero;float maxMuscle=0;
     for(int frame=0;frame<frames;frame++){
      for(int i=0;i<count;i++){source.bones[i].localRotation=new Quaternion(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());source.bones[i].localPosition=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());source.bones[i].localScale=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());}
      source.pose.GetHumanPose(ref pose);foreach(float muscle in pose.muscles){if(!float.IsFinite(muscle))throw new Exception("Non-finite source muscle");maxMuscle=Mathf.Max(maxMuscle,Mathf.Abs(muscle));}
      if(frame==0)initial=pose.bodyPosition;pose.bodyPosition=new Vector3(initial.x,pose.bodyPosition.y,initial.z);target.pose.SetHumanPose(ref pose);
      int[] aux={738,739,740,742,743,744},main={25,26,27,21,22,23};for(int k=0;k<aux.Length;k++)target.bones[aux[k]].localRotation=target.bones[main[k]].localRotation;
      foreach(int id in ids){var p=target.bones[id].localPosition;var q=target.bones[id].localRotation;writer.Write(p.x);writer.Write(p.y);writer.Write(p.z);writer.Write(q.x);writer.Write(q.y);writer.Write(q.z);writer.Write(q.w);}
     }
     report.Add(clip.name+" frames="+frames+" fps="+rate+" maxMuscle="+maxMuscle);
    }
    Debug.Log("NATIVE_HUMANOID_BAKED "+clip.name);
   }
   using(var writer=new StreamWriter(new FileStream(Path.Combine(output,"avatar-report.txt"),FileMode.CreateNew)))writer.Write(string.Join("\n",report));
   source.pose.Dispose();target.pose.Dispose();Destroy(source.root);Destroy(target.root);
  }
 }
}
