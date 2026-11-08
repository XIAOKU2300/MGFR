using System;
using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Experience;
using MGFR.Attention;

namespace MGFR.BareHands
{
 public sealed class ContactStressReview:MonoBehaviour
 {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-contact-stress")>=0)new GameObject("Contact stress review").AddComponent<ContactStressReview>();
  }
  static Pose[] Hand(Vector3 point,bool pinch=false)
  {
   var p=new Pose[26];p[0]=new Pose(Vector3.zero,Quaternion.identity);p[1]=new Pose(Vector3.down*.05f,Quaternion.identity);
   p[2]=new Pose(new Vector3(-.035f,-.025f,0),Quaternion.identity);
   for(int i=3;i<6;i++)p[i]=new Pose(p[i-1].position+new Vector3(-.015f,.025f,0),Quaternion.identity);
   for(int finger=0;finger<4;finger++)for(int j=0;j<5;j++)p[6+finger*5+j]=new Pose(new Vector3(-.03f+finger*.02f,.012f+j*.023f,0),Quaternion.identity);
   if(pinch)p[5].position=p[10].position+Vector3.left*.009f;
   var center=(p[5].position+p[10].position)*.5f;
   for(int i=0;i<26;i++)p[i].position+=point-center;
   return p;
  }
  IEnumerator Start()
  {
   var args=Environment.GetCommandLineArgs();string dir=args[Array.IndexOf(args,"-mgfr-stress-dir")+1];Directory.CreateDirectory(dir);
   BareHandInteraction hands;while((hands=FindAnyObjectByType<BareHandInteraction>())==null||!hands.IsReady)yield return null;
   hands.enabled=false;hands.Source.Replay=true;var physics=hands.Physics;physics.enabled=false;
   var loader=physics.Loader;loader.GetComponent<IdleMotionPlayer>().enabled=false;
   FindAnyObjectByType<LegPlantSolver>().enabled=false;loader.GetComponent<FaceAttentionController>().AutoUpdate=false;
   physics.ResetToAnimation();bool finite=true;float maxViolation=0,postReleasePeakSpeed=0,meanCpu=0,maxCpu=0,skirtPeak=0,hairPeak=0;
   int[] targets={Array.FindIndex(physics.Data.bodies,b=>b.name=="裙子_8_0"),Array.FindIndex(physics.Data.bodies,b=>b.name=="L_hairE_jnt8"),Array.FindIndex(physics.Data.bodies,b=>b.group==5&&b.mode==1)};
   var initial=new Vector3[physics.Bodies.Length];for(int i=0;i<initial.Length;i++)initial[i]=physics.Bodies[i].position;
   string worstBody="";int worstFrame=0;
   float hairMass=0,skirtMass=0;for(int i=0;i<physics.Bodies.Length;i++)if(!physics.Bodies[i].isKinematic)
   {if(physics.Data.bodies[i].group==4)hairMass+=physics.Bodies[i].mass;if(physics.Data.bodies[i].group==9)skirtMass+=physics.Bodies[i].mass;}
   int total=360,maxSubsteps=0;
   for(int f=0;f<total;f++)
   {
    bool tracked=f<216&&f%53!=0;int phase=Mathf.Min(f/72,2),id=targets[phase];
    Vector3 anchor=initial[id];float t=f/72f;
    Vector3 movement=new Vector3(Mathf.Sin(t*18)*.07f,Mathf.Sin(t*11)*.025f,Mathf.Cos(t*18)*.045f);
    // Rapid direction changes, tracking loss, reappearance and a discontinuity.
    if(f==108)movement+=Vector3.right*.4f;
    hands.Source.SetReplayFrame(0,Hand(loader.transform.TransformPoint(anchor+movement),f%72>18&&f%72<48),tracked);
    hands.Source.SetReplayFrame(1,Hand(loader.transform.TransformPoint(anchor+Vector3.right*.25f)),false);
    hands.StepInteraction(1f/72f);physics.Tick(f==100?.10f:1f/72f);maxSubsteps=Mathf.Max(maxSubsteps,physics.LastSubsteps);meanCpu+=physics.LastMilliseconds;maxCpu=Mathf.Max(maxCpu,physics.LastMilliseconds);
    for(int i=0;i<physics.Bodies.Length;i++)
    {
     var body=physics.Bodies[i];var p=body.position;
     finite&=!float.IsNaN(p.x)&&!float.IsNaN(p.y)&&!float.IsNaN(p.z)&&p.sqrMagnitude<25;
     float move=Vector3.Distance(p,initial[i]);
     if(physics.Data.bodies[i].group==9)skirtPeak=Mathf.Max(skirtPeak,move);
     if(physics.Data.bodies[i].group==4)hairPeak=Mathf.Max(hairPeak,move);
     if(f>288&&!body.isKinematic)postReleasePeakSpeed=Mathf.Max(postReleasePeakSpeed,body.linearVelocity.magnitude);
    }
    if(f>36)foreach(var j in physics.Joints)
    {
     var delta=j.transform.TransformPoint(j.anchor)-j.connectedBody.transform.TransformPoint(j.connectedAnchor);
     var x=j.transform.TransformDirection(j.axis).normalized;var y=j.transform.TransformDirection(j.secondaryAxis).normalized;var z=Vector3.Cross(x,y).normalized;
     float Error(ConfigurableJointMotion motion,float value)=>motion==ConfigurableJointMotion.Free?0:Mathf.Max(0,Mathf.Abs(value)-(motion==ConfigurableJointMotion.Locked?0:j.linearLimit.limit));
     float violation=Mathf.Max(Error(j.xMotion,Vector3.Dot(delta,x)),Mathf.Max(Error(j.yMotion,Vector3.Dot(delta,y)),Error(j.zMotion,Vector3.Dot(delta,z))));
     if(violation>maxViolation){maxViolation=violation;worstBody=j.name;worstFrame=f;}
    }
    if(f%18==0)yield return null;
   }
   bool pass=finite&&maxViolation<.035f&&postReleasePeakSpeed<1&&hands.GrabbedBody[0]<0&&hands.ActiveColliders==0&&hands.HairGrabStarts>0&&hands.HandProxiesIgnoreEachOther&&maxSubsteps<=3;
   string report=$"pass={pass}\nsource=SYNTHETIC_CONTACT_NOT_HEADSET\nframes={total}\nfiniteBounds={finite}\nmaxConstraintViolationMetres={maxViolation}\nworstBody={worstBody}\nworstFrame={worstFrame}\npostReleasePeakSpeedMetresPerSecond={postReleasePeakSpeed}\nskirtPeakMovementMetres={skirtPeak}\nhairPeakMovementMetres={hairPeak}\nmeanPhysicsCpuMs={meanCpu/total}\nmaxPhysicsCpuMs={maxCpu}\nhairDynamicMassKg={hairMass}\nskirtDynamicMassKg={skirtMass}\ncontacts={hands.FingerContacts}\ngrabs={hands.GrabStarts}\ntrackingLossReleases={hands.GrabbedBody[0]<0&&hands.ActiveColliders==0}\n";
   report+=$"hairGrabs={hands.HairGrabStarts}\nmaxSubstepsIncluding100msHitch={maxSubsteps}\nhandSelfCollisionDisabled={hands.HandProxiesIgnoreEachOther}\n";
   File.WriteAllText(Path.Combine(dir,"contact-stress.txt"),report);Debug.Log("[MGFR contact stress] "+report.Replace('\n',' '));Application.Quit(pass?0:1);
  }
 }
}
