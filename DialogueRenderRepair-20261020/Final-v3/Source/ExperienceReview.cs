using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Diagnostics;
using UnityEngine;
using MGFR.Skins;
using MGFR.Skins.ClothPhysics;
using MGFR.Dialogue;
using MGFR.BareHands;
using MGFR.Character;

namespace MGFR.StructuredVoiceFinal {
 [DefaultExecutionOrder(3010)]public sealed class ExperienceReview:MonoBehaviour {
  [Serializable]public class SolverCheck {public bool pass;public int steps,particles,constraints;public float maxPositionError,maxPreviousError,maxProjectionError,referenceStepMeanMs,cachedStepMeanMs;}
  [Serializable]public class Report {public bool pass,returnedToIdle,skinSwitch,playedStart,playedLoop,playedEnd,interruptedToIdle,delayedCueWaited,twoHandsContact,clothGrabLeft,clothGrabRight,trackingLossReleases;public SolverCheck solver;public ExperiencePerformance.Summary[] performance;public string evidence="Isolated real Unity player, installed meshes and native actions, synthetic observed hand joints and speech signals; no headset, ALVR or remote LLM";}
  MainAvatarActions driver;SiSkinSwitcher skins;SwimsuitClothRuntime cloth;NativeClothCoordinator coordinator;string output;
  int sequence=90000;readonly List<ExperiencePerformance.Summary> summaries=new List<ExperiencePerformance.Summary>();
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-experience-out")+1];Directory.CreateDirectory(output);
   AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   QualitySettings.vSyncCount=0;Application.targetFrameRate=72;
   float deadline=Time.realtimeSinceStartup+60;
   while((driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready||(skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||(cloth=FindAnyObjectByType<SwimsuitClothRuntime>())==null||cloth.Solver==null){if(Time.realtimeSinceStartup>deadline){Application.Quit(4);yield break;}yield return null;}
   coordinator=FindAnyObjectByType<NativeClothCoordinator>();driver.ReviewOverride=true;driver.ReviewSpeaking=false;
   var result=new Report();yield return new WaitForSeconds(1);
   result.solver=CompareSolver();
   yield return new WaitForSeconds(.5f);
   ExperiencePerformance.Instance.Begin("idle-swimsuit");for(int i=0;i<180;i++)yield return null;summaries.Add(ExperiencePerformance.Instance.End());
   Plan("arms_crossed");result.playedStart=false;result.playedLoop=false;result.playedEnd=false;
   ExperiencePerformance.Instance.Begin("state-family-swimsuit");
   float stop=Time.realtimeSinceStartup+13;
   while(Time.realtimeSinceStartup<stop){
    string action=driver.CurrentAction;result.playedStart|=action=="story_dialog_state_chesthugging1_start";result.playedLoop|=action=="arms_crossed";result.playedEnd|=action=="story_dialog_state_chesthugging1_end";yield return null;
   }
   summaries.Add(ExperiencePerformance.Instance.End());driver.ReviewSpeaking=false;
   yield return new WaitForSeconds(1);result.returnedToIdle=driver.CurrentAction=="idle";
   Plan("think");yield return new WaitForSeconds(.8f);float clock=driver.MotionClock;
   result.skinSwitch=skins.TrySelect("original");yield return null;result.skinSwitch&=Mathf.Abs(driver.MotionClock-clock)<.15f;
   yield return new WaitForSeconds(.5f);
   ExperiencePerformance.Instance.Begin("motion-original");for(int i=0;i<180;i++)yield return null;summaries.Add(ExperiencePerformance.Instance.End());
   result.skinSwitch&=skins.TrySelect("swimsuit");yield return new WaitForSeconds(.5f);
   driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=driver.ReviewOverride?0:-1,emotion="neutral",expression_variant="neutral_relaxed",actions=new ActionCue[0]});driver.ReviewSpeaking=false;
   yield return new WaitForSeconds(.5f);result.interruptedToIdle=driver.CurrentAction=="idle";
   driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=0,emotion="neutral",expression_variant="neutral_relaxed",actions=new[]{new ActionCue{name="nod",at=1,duration=1.33334f}}});
   driver.ReviewSpeaking=false;yield return new WaitForSeconds(.3f);result.delayedCueWaited=driver.CurrentAction=="idle";
   driver.ReviewSpeaking=true;yield return new WaitForSeconds(.6f);result.delayedCueWaited&=driver.CurrentAction=="idle";
   yield return new WaitForSeconds(.6f);result.delayedCueWaited&=driver.CurrentAction=="nod";
   driver.ReviewSpeaking=false;yield return new WaitForSeconds(2);
   var hands=FindAnyObjectByType<BareHandInteraction>();hands.PreferBareHands=true;hands.Source.Replay=true;
   var poses=new[]{new Pose[26],new Pose[26]};var points=new Vector3[2];var selected=new int[2];
   for(int h=0;h<2;h++){
    float best=float.PositiveInfinity;
    for(int i=0;i<cloth.Solver.Particles.Length;i++){var p=cloth.Solver.Particles[i];if(p.group!=h||p.inverseMass<.5f||p.position.z>=best)continue;selected[h]=i;best=p.position.z;}
    points[h]=cloth.Solver.Particles[selected[h]].position;
   }
   for(int frame=0;frame<30;frame++){for(int h=0;h<2;h++){points[h]=cloth.Solver.Particles[selected[h]].position;FillHand(poses[h],points[h],false);hands.Source.SetReplayFrame(h,poses[h],true);}yield return null;}
   ExperiencePerformance.Instance.Begin("two-hand-cloth-grab");
   for(int frame=0;frame<180;frame++){
    for(int h=0;h<2;h++){FillHand(poses[h],points[h]+Vector3.back*(Mathf.Min(frame,120)/120f*.025f),true);hands.Source.SetReplayFrame(h,poses[h],true);}
    result.twoHandsContact|=hands.ActiveColliders==40;
    result.clothGrabLeft|=cloth.Solver.Grips[0].particle>=0;result.clothGrabRight|=cloth.Solver.Grips[1].particle>=0;yield return null;
   }
   summaries.Add(ExperiencePerformance.Instance.End());
   for(int h=0;h<2;h++)hands.Source.SetReplayFrame(h,poses[h],false);
   yield return new WaitForSeconds(.15f);result.trackingLossReleases=cloth.Solver.Grips[0].particle<0&&cloth.Solver.Grips[1].particle<0;
   FillHand(poses[0],skins.Loader.transform.TransformPoint(new Vector3(0,1.12f,-.18f)),false);hands.Source.SetReplayFrame(0,poses[0],true);
   yield return null;yield return null;Snapshot("hand-occlusion-clean.png");hands.Source.SetReplayFrame(0,poses[0],false);
   result.performance=summaries.ToArray();
   result.pass=result.solver.pass&&result.returnedToIdle&&result.skinSwitch&&result.interruptedToIdle&&result.delayedCueWaited&&result.playedStart&&result.playedLoop&&result.playedEnd&&result.twoHandsContact&&result.clothGrabLeft&&result.clothGrabRight&&result.trackingLossReleases;
   using(var w=new StreamWriter(new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew)))w.Write(JsonUtility.ToJson(result,true));
   UnityEngine.Debug.Log("EXPERIENCE_REVIEW_"+(result.pass?"PASS":"FAIL"));Application.Quit(result.pass?0:5);
  }
  void Plan(string name){driver.SetReviewPlan(new SpeechPlan{sequence=sequence++,voice_round=0,emotion="neutral",expression_variant="neutral_relaxed",actions=new[]{new ActionCue{name=name,at=0,duration=30}}});driver.ReviewSpeaking=true;}
  static void FillHand(Pose[] poses,Vector3 point,bool pinch){
   for(int i=0;i<26;i++)poses[i]=new Pose(Vector3.zero,Quaternion.identity);
   poses[1].position=new Vector3(0,-.05f,0);poses[2].position=new Vector3(-.035f,-.025f,0);poses[3].position=new Vector3(-.05f,0,0);poses[4].position=new Vector3(-.06f,.025f,0);poses[5].position=new Vector3(-.065f,.05f,0);
   for(int finger=0;finger<4;finger++)for(int joint=0;joint<5;joint++)poses[6+finger*5+joint].position=new Vector3(-.03f+finger*.02f,.012f+joint*.023f,0);
   if(pinch){poses[5].position=poses[10].position+new Vector3(-.009f,0,-.003f);poses[4].position=(poses[3].position+poses[5].position)*.5f;}
   var offset=(poses[5].position+poses[10].position)*.5f;for(int i=0;i<26;i++)poses[i].position+=point-offset;
  }
  void Snapshot(string name){
   var camera=FindAnyObjectByType<SiCharacterBootstrap>().SceneCamera;var target=camera.targetTexture;var position=camera.transform.position;var rotation=camera.transform.rotation;bool orthographic=camera.orthographic;float size=camera.orthographicSize;
   camera.orthographic=true;camera.orthographicSize=1f;var center=skins.Loader.transform.position+Vector3.up*.88f;camera.transform.position=center+Vector3.back*3;camera.transform.LookAt(center);
   var rt=new RenderTexture(800,1000,24);camera.targetTexture=rt;camera.Render();var previous=RenderTexture.active;RenderTexture.active=rt;
   var image=new Texture2D(800,1000,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,800,1000),0,0);image.Apply();File.WriteAllBytes(Path.Combine(output,name),image.EncodeToPNG());
   RenderTexture.active=previous;camera.targetTexture=target;camera.orthographic=orthographic;camera.orthographicSize=size;camera.transform.SetPositionAndRotation(position,rotation);Destroy(image);rt.Release();Destroy(rt);
  }
  SolverCheck CompareSolver(){
   var solver=cloth.Solver;var type=typeof(SwimsuitClothRuntime);const BindingFlags flags=BindingFlags.Instance|BindingFlags.NonPublic;
   var body=(List<SwimsuitClothSolver.Capsule>)type.GetField("body",flags).GetValue(cloth);
   var hands=(List<SwimsuitClothSolver.Capsule>[])type.GetField("handCapsules",flags).GetValue(cloth);
   var initial=(SwimsuitClothSolver.Particle[])solver.Particles.Clone();var common=(SwimsuitClothSolver.Particle[])initial.Clone();
   var expected=new SwimsuitClothSolver.Particle[initial.Length];var cached=new CachedClothStep(solver);
   var saved=(SwimsuitClothSolver.Grip[])solver.Grips.Clone();var savedGroups=(bool[])solver.EnabledGroups.Clone();
   double referenceTime=0,cachedTime=0;float positionError=0,previousError=0,projectionError=0;
   var finish=typeof(NativeClothCoordinator).GetMethod("FinishBodyContacts",flags);
   var watch=new Stopwatch();
   try{
    for(int frame=0;frame<120;frame++){
     // Exercise both grips, moving targets, disabled garment groups and frame intervals.
     if(frame==20||frame==60){int selected=0;while(selected<common.Length-1&&common[selected].inverseMass<=0)selected++;solver.Grips[frame==20?0:1]=new SwimsuitClothSolver.Grip{particle=selected,target=common[selected].target+new Vector3(.015f,.01f,0)};}
     if(frame==80)solver.EnabledGroups[1]=false;
     if(frame==100){solver.EnabledGroups[1]=true;solver.Release(0);solver.Release(1);}
     float delta=frame%3==0?.0222f:frame%3==1?.0138889f:.0083333f;var wind=new Vector3(.08f,0,.025f);
     Array.Copy(common,solver.Particles,common.Length);watch.Restart();solver.Step(delta,body,hands,wind);watch.Stop();referenceTime+=watch.Elapsed.TotalMilliseconds;Array.Copy(solver.Particles,expected,expected.Length);
     Array.Copy(common,solver.Particles,common.Length);watch.Restart();cached.Step(delta,body,hands,wind);watch.Stop();cachedTime+=watch.Elapsed.TotalMilliseconds;
     for(int i=0;i<common.Length;i++){positionError=Mathf.Max(positionError,Vector3.Distance(solver.Particles[i].position,expected[i].position));previousError=Mathf.Max(previousError,Vector3.Distance(solver.Particles[i].previous,expected[i].previous));}
     Array.Copy(expected,solver.Particles,expected.Length);ReferenceProjection(expected,body,solver.EnabledGroups);
     finish.Invoke(coordinator,new object[]{solver});
     for(int i=0;i<common.Length;i++)projectionError=Mathf.Max(projectionError,Vector3.Distance(solver.Particles[i].position,expected[i].position),Vector3.Distance(solver.Particles[i].previous,expected[i].previous));
     Array.Copy(expected,common,common.Length);
    }
   }finally{Array.Copy(initial,solver.Particles,initial.Length);Array.Copy(saved,solver.Grips,2);Array.Copy(savedGroups,solver.EnabledGroups,4);}
   return new SolverCheck{pass=positionError<.0001f&&previousError<.0001f&&projectionError<.000001f,steps=120,particles=initial.Length,constraints=solver.ConstraintCount,maxPositionError=positionError,maxPreviousError=previousError,maxProjectionError=projectionError,referenceStepMeanMs=(float)(referenceTime/120),cachedStepMeanMs=(float)(cachedTime/120)};
  }
  struct Shape {public Vector3 a,axis,min,max;public float radius,inverse;}
  static void ReferenceProjection(SwimsuitClothSolver.Particle[] particles,List<SwimsuitClothSolver.Capsule> body,bool[] enabled){
   int count=Mathf.Min(body.Count,80);var shapes=new Shape[count];
   for(int c=0;c<count;c++){var capsule=body[c];var axis=capsule.b-capsule.a;var margin=Vector3.one*capsule.radius;shapes[c]=new Shape{a=capsule.a,axis=axis,min=Vector3.Min(capsule.a,capsule.b)-margin,max=Vector3.Max(capsule.a,capsule.b)+margin,radius=capsule.radius,inverse=axis.sqrMagnitude>1e-10f?1/axis.sqrMagnitude:0};}
   for(int iteration=0;iteration<8;iteration++)for(int i=0;i<particles.Length;i++){
    var p=particles[i];if(p.inverseMass==0||!enabled[p.group])continue;
    for(int c=0;c<count;c++){var shape=shapes[c];var v=p.position;if(v.x<shape.min.x||v.x>shape.max.x||v.y<shape.min.y||v.y>shape.max.y||v.z<shape.min.z||v.z>shape.max.z)continue;
     float t=Mathf.Clamp01(Vector3.Dot(v-shape.a,shape.axis)*shape.inverse);var normal=v-(shape.a+shape.axis*t);float squared=normal.sqrMagnitude;
     if(squared>=shape.radius*shape.radius||squared<1e-12f)continue;var correction=normal*(shape.radius/Mathf.Sqrt(squared)-1);p.position+=correction;p.previous+=correction;
    }particles[i]=p;
   }
  }
 }
}
