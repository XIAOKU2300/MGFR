using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEngine;
using MGFR.BareHands;
using MGFR.Attention;
using MGFR.PhysicsRig;

namespace MGFR.Experience
{
 public sealed class ClothMotionReview:MonoBehaviour
 {
  [Serializable]class Report
  {
   public string source="ACTUAL_RIG_ANIMATED_WITH_PHYSX_NOT_HEADSET";
   public bool pass,finite;public int frames,fastBodies,penetratingSamples;
   public float maxJointError,maxBodySpeed,meanPhysicsMs,maxPhysicsMs,maxPenetration,meanPenetration,maxFrameDisplacement;
   public int softFabricLinks,worstPenetrationFrame,handContacts,hairGrabs;public float maxPenetrationAfterFirstSecond;
   public string worstJoint,worstBody,worstPenetration;public int worstFrame;
  }
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-cloth-motion-review")>=0)new GameObject("Motion and cloth review").AddComponent<ClothMotionReview>();}
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string dir=args[Array.IndexOf(args,"-mgfr-cloth-dir")+1];Directory.CreateDirectory(dir);
   bool withHands=Array.IndexOf(args,"-mgfr-cloth-with-hands")>=0;
   BareHandInteraction hands;while((hands=FindAnyObjectByType<BareHandInteraction>())==null||!hands.IsReady)yield return null;
   hands.enabled=false;hands.Source.Replay=true;hands.Source.SetReplayFrame(0,null,false);hands.Source.SetReplayFrame(1,null,false);hands.StepInteraction(1f/72);
   var p=hands.Physics;p.enabled=false;var loader=p.Loader;var idle=loader.GetComponent<IdleMotionPlayer>();idle.enabled=false;
   var face=loader.GetComponent<FaceAttentionController>();face.AutoUpdate=false;
   var leg=FindAnyObjectByType<LegPlantSolver>();leg.enabled=false;var legTick=typeof(LegPlantSolver).GetMethod("LateUpdate",BindingFlags.Instance|BindingFlags.NonPublic);
   var cols=new Collider[p.Bodies.Length];var previous=new Vector3[cols.Length];var torso=new List<int>();
   for(int i=0;i<cols.Length;i++){cols[i]=p.Bodies[i].GetComponent<Collider>();previous[i]=p.Bodies[i].position;if(p.Bodies[i].isKinematic&&p.Data.bodies[i].group==0)torso.Add(i);}
   var r=new Report{finite=true,frames=1080};float penetrationTotal=0;int overlapCount=0;
   var phrases=new[]{"你好，给你看看，我当然可以陪你聊一会儿。","你好，挥挥手。","来，看左边那个。","想一想，不是的。"};
   int hair=Array.FindIndex(p.Data.bodies,b=>b.name=="L_hairE_jnt8");Vector3 handAnchor=Vector3.zero;
   idle.ReviewPlayback(false,0,0,1f/72);idle.Apply(0,1f/72);legTick.Invoke(leg,null);p.ResetToAnimation();
   for(int warm=0;warm<8;warm++)p.Tick(1f/120);
   for(int f=0;f<r.frames;f++)
   {
    float now=f/72f;int phase=f/180;bool speaking=phase==1||phase==2||phase==4||phase==5;
    if(f%180==0&&speaking)idle.Gestures.Queue(phase,0,phrases[(phase-1)%phrases.Length],0);
    idle.ReviewPlayback(speaking,phase,now,1f/72);
    idle.Gestures.Tick(phase,(long)(f%180*48000d/72),48000,speaking,speaking,now,1f/72,face);
    idle.Apply(now,1f/72);legTick.Invoke(leg,null);face.SubmitHeadGesture(idle.Gestures.Head,now);face.Tick(now,1f/72);
    if(withHands)
    {
     if(f==900)handAnchor=p.Bodies[hair].position;
     bool tracked=f>=900&&f<1030;
     Vector3 target=handAnchor+new Vector3(Mathf.Clamp01((f-925)/50f)*.05f,0,-.008f);
     hands.Source.SetReplayFrame(0,tracked?Hand(loader.transform.TransformPoint(target),f>=925&&f<1000):null,tracked);
     hands.StepInteraction(1f/72);
    }
    p.Tick(f==440?.09f:1f/72);r.meanPhysicsMs+=p.LastMilliseconds;r.maxPhysicsMs=Mathf.Max(r.maxPhysicsMs,p.LastMilliseconds);
    foreach(var j in p.Joints)
    {
     Vector3 delta=j.transform.TransformPoint(j.anchor)-j.connectedBody.transform.TransformPoint(j.connectedAnchor);
     Vector3 x=j.transform.TransformDirection(j.axis).normalized,y=j.transform.TransformDirection(j.secondaryAxis).normalized,z=Vector3.Cross(x,y).normalized;
     float E(ConfigurableJointMotion m,float v)=>m==ConfigurableJointMotion.Free?0:Mathf.Max(0,Mathf.Abs(v)-(m==ConfigurableJointMotion.Locked?0:j.linearLimit.limit));
     float error=Mathf.Max(E(j.xMotion,Vector3.Dot(delta,x)),Mathf.Max(E(j.yMotion,Vector3.Dot(delta,y)),E(j.zMotion,Vector3.Dot(delta,z))));
     if(f>60&&error>r.maxJointError){r.maxJointError=error;r.worstJoint=j.name;r.worstFrame=f;}
    }
    for(int i=0;i<cols.Length;i++)if(!p.Bodies[i].isKinematic)
    {
     var body=p.Bodies[i];r.finite&=float.IsFinite(body.position.sqrMagnitude)&&body.position.sqrMagnitude<25;
     float speed=body.linearVelocity.magnitude;if(speed>3)r.fastBodies++;
     if(f>60&&speed>r.maxBodySpeed){r.maxBodySpeed=speed;r.worstBody=p.Data.bodies[i].name;}
     if(f>60)r.maxFrameDisplacement=Mathf.Max(r.maxFrameDisplacement,Vector3.Distance(previous[i],body.position));previous[i]=body.position;
     if(f%12!=0||p.Data.bodies[i].group<4)continue;
     foreach(int t in torso)
     {
      if(UnityEngine.Physics.GetIgnoreCollision(cols[i],cols[t])||!cols[i].bounds.Intersects(cols[t].bounds))continue;
      if(UnityEngine.Physics.ComputePenetration(cols[i],body.position,body.rotation,cols[t],p.Bodies[t].position,p.Bodies[t].rotation,out _,out float distance))
      {
       penetrationTotal+=distance;overlapCount++;if(distance>.005f)r.penetratingSamples++;
       if(f>=72)r.maxPenetrationAfterFirstSecond=Mathf.Max(r.maxPenetrationAfterFirstSecond,distance);
       if(distance>r.maxPenetration){r.maxPenetration=distance;r.worstPenetration=p.Data.bodies[i].name+" / "+p.Data.bodies[t].name;r.worstPenetrationFrame=f;}
      }
     }
    }
    if(f==300||f==430||f==680||f==980)Snapshot(Path.Combine(dir,"frame-"+f+".png"),loader.transform);
    if(f%36==0)yield return null;
   }
   r.meanPhysicsMs/=r.frames;r.meanPenetration=penetrationTotal/Mathf.Max(1,overlapCount);r.softFabricLinks=p.SoftLinkCount;
   r.handContacts=hands.FingerContacts;r.hairGrabs=hands.HairGrabStarts;
   r.pass=r.finite&&r.maxJointError<.015f&&r.maxBodySpeed<3&&r.maxPenetration<.025f;
   if(withHands){r.source+="_WITH_PUSH_AND_PINCH";r.pass&=r.handContacts>0&&r.hairGrabs>0;}
   File.WriteAllText(Path.Combine(dir,"motion-cloth.json"),JsonUtility.ToJson(r,true));Debug.Log("[MGFR motion cloth review] "+JsonUtility.ToJson(r));Application.Quit(r.pass?0:1);
  }
  static Pose[] Hand(Vector3 target,bool pinch)
  {
   var p=new Pose[26];p[0]=new Pose(Vector3.zero,Quaternion.identity);p[1]=new Pose(Vector3.down*.05f,Quaternion.identity);
   p[2]=new Pose(new Vector3(-.035f,-.025f,0),Quaternion.identity);
   for(int i=3;i<6;i++)p[i]=new Pose(p[i-1].position+new Vector3(-.015f,.025f,0),Quaternion.identity);
   for(int finger=0;finger<4;finger++)for(int j=0;j<5;j++)p[6+finger*5+j]=new Pose(new Vector3(-.03f+finger*.02f,.012f+j*.023f,0),Quaternion.identity);
   if(pinch)p[5].position=p[10].position+Vector3.left*.009f;
   Vector3 center=(p[5].position+p[10].position)*.5f;for(int i=0;i<26;i++)p[i].position+=target-center;return p;
  }
  static void Snapshot(string path,Transform actor)
  {
   var camera=Camera.main;var pos=camera.transform.position;var rot=camera.transform.rotation;var old=camera.targetTexture;var active=RenderTexture.active;
   camera.transform.position=actor.position+actor.TransformDirection(Vector3.back)*2.2f+Vector3.up*.95f;camera.transform.LookAt(actor.position+Vector3.up*.94f);
   var target=new RenderTexture(900,1000,24);camera.targetTexture=target;camera.Render();RenderTexture.active=target;
   var image=new Texture2D(900,1000,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,900,1000),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());
   RenderTexture.active=active;camera.targetTexture=old;camera.transform.SetPositionAndRotation(pos,rot);target.Release();Destroy(target);Destroy(image);
  }
 }
}
