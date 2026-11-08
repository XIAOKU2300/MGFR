using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.BareHands;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Skins;

namespace MGFR.GesturePanel {
 public sealed class GesturePanelReview:MonoBehaviour {
  [Serializable]public class Check {public string name;public bool pass;public float value;}
  [Serializable]public class Result {public bool pass;public Check[] checks;public string evidence="Actual current player and meshes; synthetic anatomical hand samples, no microphone, remote LLM or headset interaction";}
  readonly List<Check> checks=new List<Check>();string output;
  void CheckResult(string name,bool pass,float value=0){checks.Add(new Check{name=name,pass=pass,value=value});Debug.Log("HAND_PANEL_CHECK "+name+"="+pass);}
  public static HandFrame Fixture(float now,bool fist,bool pinch=false,Vector3 shift=default){
   var frame=new HandFrame{Tracked=true,Timestamp=now,ValidCount=26,ObservedCount=26};for(int i=0;i<26;i++){frame.Valid[i]=frame.Observed[i]=true;frame.Radius[i]=.008f;frame.Joints[i]=new Pose(shift,Quaternion.identity);}
   void Put(int j,Vector3 p){frame.Joints[j]=new Pose(shift+p,Quaternion.identity);}
   Put(0,Vector3.zero);Put(1,new Vector3(0,-.05f,0));Put(2,new Vector3(-.05f,-.02f,0));Put(3,new Vector3(-.05f,0,-.01f));Put(4,new Vector3(-.032f,.005f,-.025f));Put(5,fist?new Vector3(-.012f,.006f,-.030f):new Vector3(-.070f,.025f,0));
   int[] keys={7,12,17,22};float[] x={-.025f,0,.022f,.04f};
   for(int f=0;f<4;f++){int k=keys[f];var p=new Vector3(x[f],.03f,0);Put(k-1,p-Vector3.up*.025f);Put(k,p);
    Put(k+1,p+(fist?new Vector3(0,.015f,-.023f):Vector3.up*.032f));Put(k+2,p+(fist?new Vector3(0,-.012f,-.037f):Vector3.up*.055f));Put(k+3,p+(fist?new Vector3(0,-.032f,-.022f):Vector3.up*.074f));
   }
   if(pinch){Put(5,new Vector3(-.027f,.04f,-.02f));Put(10,new Vector3(-.013f,.04f,-.02f));}return frame;
  }
  void IntentChecks(){
   foreach(int fps in new[]{30,72,120}){
    var gate=new FistSummonGate();float t=1;int fired=0;float first=0;
    for(int i=0;i<fps*.4f;i++){gate.Step(Fixture(t,false),t,true,false,false);t+=1f/fps;}
    float begin=t;for(int i=0;i<fps*3.4f;i++){if(gate.Step(Fixture(t,true),t,true,false,false)){fired++;if(first==0)first=t-begin;}t+=1f/fps;}
    CheckResult("fist_after_three_seconds_"+fps,fired==1&&first>3&&first<3.1f,first);
    for(int i=0;i<fps*4;i++){if(gate.Step(Fixture(t,true),t,true,false,false))fired++;t+=1f/fps;}
    CheckResult("held_fist_does_not_repeat_"+fps,fired==1);
   }
   string[] cases={"cold_closed_hand","pinch","controller_pose","character_or_cloth_owned","stale_samples","missing_observed_tip","loss_then_closed","fast_hand"};
   foreach(string name in cases){var gate=new FistSummonGate();int fires=0;float t=1;
    if(name!="cold_closed_hand")for(int i=0;i<35;i++){gate.Step(Fixture(t,false),t,true,false,false);t+=.01f;}
    for(int i=0;i<450;i++){var f=Fixture(t,true,name=="pinch",name=="fast_hand"?new Vector3(t*.5f,0,0):Vector3.zero);
     if(name=="pinch")f=Fixture(t,false,true);
     if(name=="stale_samples")f.Timestamp=1;
     if(name=="missing_observed_tip")f.Observed[15]=false;
     if(name=="loss_then_closed"&&i==250)f.Tracked=false;
     if(gate.Step(f,t,name!="controller_pose",name=="character_or_cloth_owned",false))fires++;t+=.01f;
    }CheckResult(name,fires==0,fires);
   }
   var interrupted=new FistSummonGate();float now=1;for(int i=0;i<35;i++){interrupted.Step(Fixture(now,false),now,true,false,false);now+=.01f;}for(int i=0;i<299;i++){interrupted.Step(Fixture(now,true),now,true,false,false);now+=.01f;}interrupted.Step(Fixture(now,true),now,true,true,false);now+=.01f;int after=0;for(int i=0;i<400;i++){if(interrupted.Step(Fixture(now,true),now,true,false,false))after++;now+=.01f;}CheckResult("contact_resets_almost_complete_hold",after==0);
  }
  void TouchChecks(){
   var gate=new FingerTouchGate();float now=1;int count=0;
   void Step(float z,int hit=0,bool valid=true,float hold=0){int action=gate.Step(valid,now,new Vector3(0,0,z),.008f,hit,GesturePanelVisual.SurfaceZ,now,hold);if(action>=0)count++;now+=.01f;}
   for(int i=0;i<20;i++)Step(-.12f);for(int i=0;i<20;i++)Step(-.024f);CheckResult("front_touch_fires_once",count==1);
   for(int i=0;i<150;i++)Step(-.024f);CheckResult("held_button_does_not_repeat",count==1);
   for(int i=0;i<20;i++)Step(-.12f);for(int i=0;i<20;i++)Step(-.024f);CheckResult("retreat_allows_next_press",count==2);
   gate.Reset();count=0;for(int i=0;i<20;i++)Step(.015f);for(int i=0;i<30;i++)Step(-.024f);CheckResult("backside_touch_rejected",count==0);
   gate.Reset();for(int i=0;i<20;i++)Step(-.12f);for(int i=0;i<4;i++)Step(-.024f,0,true,.35f);Step(-.024f,0,false,.35f);for(int i=0;i<30;i++)Step(-.024f,0,true,.35f);CheckResult("tracking_loss_cancels_pending_press",count==0);
   gate.Reset();for(int i=0;i<20;i++)Step(-.12f);for(int i=0;i<30;i++)Step(-.024f,-1);CheckResult("gaps_do_not_activate",count==0);
  }
  void SensitivityChecks(){
   foreach(int fps in new[]{30,72,120}){
    var gate=new FingerTouchGate();float now=1;int presses=0;
    foreach(float z in new[]{-.10f,-.06f,-.03f,.02f,.065f}){if(gate.Step(true,now,new Vector3(0,0,z),.008f,0,GesturePanelVisual.SurfaceZ,now)>=0)presses++;now+=1f/fps;}
    CheckResult("fast_poke_crossing_registers_once_"+fps,presses==1,presses);
   }
   var deep=new FingerTouchGate();float time=1;int fired=0;
   for(int i=0;i<20;i++){deep.Step(true,time,new Vector3(0,0,-.08f),.008f,0,GesturePanelVisual.SurfaceZ,time);time+=.01f;}
   if(deep.Step(true,time,new Vector3(0,0,.07f),.008f,0,GesturePanelVisual.SurfaceZ,time)>=0)fired++;
   CheckResult("sample_can_cross_entire_panel_without_missing_touch",fired==1,fired);
   var near=new FingerTouchGate();near.Step(true,1,new Vector3(0,0,-.052f),.008f,0,GesturePanelVisual.SurfaceZ,1);
   int immediate=near.Step(true,1.014f,new Vector3(0,0,-.030f),.008f,0,GesturePanelVisual.SurfaceZ,1.014f);
   CheckResult("near_front_touch_requires_no_dwell",immediate==0);
   near.Step(true,1.028f,new Vector3(0,0,-.052f),.008f,0,GesturePanelVisual.SurfaceZ,1.028f);
   CheckResult("short_retreat_rearms_without_pause",near.Step(true,1.042f,new Vector3(0,0,-.030f),.008f,0,GesturePanelVisual.SurfaceZ,1.042f)==0);
   var occluded=Fixture(1,false);foreach(int j in new[]{15,20,25})occluded.Observed[j]=false;
   CheckResult("other_finger_occlusion_does_not_block_index",HandMenuPose.FreshTouch(occluded,1)&&HandMenuPose.Pointer(occluded)&&!HandMenuPose.Fresh(occluded,1));
   occluded.Observed[10]=false;CheckResult("unobserved_index_still_rejected",!HandMenuPose.FreshTouch(occluded,1));
   var curved=Fixture(1,false);curved.Joints[10]=new Pose(curved.Joints[9].position+new Vector3(0,.012f,-.015f),Quaternion.identity);
   CheckResult("naturally_curved_index_is_accepted",HandMenuPose.FreshTouch(curved,1)&&HandMenuPose.Pointer(curved));
   CheckResult("closed_fist_is_not_a_touch_pointer",!HandMenuPose.Pointer(Fixture(1,true)));
   var sweep=new FingerTouchGate();sweep.Step(true,1,new Vector3(-.10f,0,-.08f),.008f,0,GesturePanelVisual.SurfaceZ,1);
   var crossing=sweep.ContactPoint(new Vector3(.10f,0,.07f),.008f,GesturePanelVisual.SurfaceZ,1.02f);
   CheckResult("diagonal_poke_tests_front_crossing_position",crossing.x<0&&crossing.x>-.10f,crossing.x);
   var longPress=new FingerTouchGate();float clock=1;int restores=0;
   void Long(float z){if(longPress.Step(true,clock,new Vector3(0,0,z),.008f,0,GesturePanelVisual.SurfaceZ,clock,.35f)>=0)restores++;clock+=.01f;}
   Long(-.08f);for(int i=0;i<20;i++)Long(-.024f);CheckResult("restore_keeps_deliberate_hold",restores==0);Long(.07f);for(int i=0;i<40;i++)Long(.07f);CheckResult("deep_fast_poke_does_not_restore_clothing",restores==0);
   Long(-.08f);for(int i=0;i<45;i++)Long(-.024f);CheckResult("deliberate_restore_hold_works",restores==1);
  }
  IEnumerator Start(){
   var args=Environment.GetCommandLineArgs();output=args[Array.IndexOf(args,"-mgfr-hand-menu-out")+1];if(Directory.Exists(output))throw new InvalidOperationException("Review output exists");Directory.CreateDirectory(output);AudioListener.volume=0;
   var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;
   IntentChecks();TouchChecks();SensitivityChecks();float deadline=Time.realtimeSinceStartup+45;GesturePanelRuntime runtime;
   while((runtime=FindAnyObjectByType<GesturePanelRuntime>())==null||!runtime.Ready){if(Time.realtimeSinceStartup>deadline){Application.Quit(2);yield break;}yield return null;}
   var old=FindAnyObjectByType<ControllerActions>();CheckResult("old_button_menu_retired",old!=null&&!old.enabled&&old.View!=null&&!old.View.Shown);
   var camera=new GameObject("Gesture panel desktop review").AddComponent<Camera>();camera.CopyFrom(Camera.main);camera.enabled=false;camera.stereoTargetEye=StereoTargetEyeMask.None;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.10f,.12f,.14f);camera.allowHDR=false;camera.allowMSAA=false;camera.fieldOfView=54;
   var position=new Vector3(0,1.30f,-1.0f);var rotation=Quaternion.identity;runtime.ReviewOpen(position,rotation);yield return new WaitForSeconds(.42f);
   var anchored=runtime.View.Panel.position;camera.transform.position=position+new Vector3(.02f,.015f,-.80f);camera.transform.LookAt(position);
   CheckResult("subtitles_do_not_occlude_open_panel",runtime.CaptionsSuppressed);
   var released=Fixture(Time.unscaledTime,false);foreach(int j in new[]{15,20,25})released.Observed[j]=false;
   CheckResult("pointing_releases_summon_without_full_open_hand_dwell",runtime.ReviewRelease(released,Time.unscaledTime));
   int mainGap=runtime.View.Hit(new Vector2(0,.05f));CheckResult("thirty_mm_main_gap_is_inactive",mainGap<0);
   for(int i=0;i<runtime.View.Controls.Count;i++){var item=runtime.View.Controls[i];CheckResult("target_center_"+item.key,item.disabled||runtime.View.Hit(item.rect.center)==i);}
   var first=runtime.View.Controls[3].rect;var secondRow=runtime.View.Controls[5].rect;CheckResult("main_rows_at_least_24mm_apart",first.yMin-secondRow.yMax>=.024f,first.yMin-secondRow.yMax);
   CheckResult("visible_key_edge_is_touchable",runtime.View.Hit(new Vector2(first.xMin+.002f,first.center.y))==3);
   Save(camera,output,"01-common-front.png");
   bool muted=auto!=null&&auto.Muted;if(auto!=null){runtime.Activate("voice");CheckResult("voice_toggle_uses_real_component",auto.Muted!=muted);runtime.Activate("voice");}
   var caption=FindAnyObjectByType<CameraChatOverlay>();if(caption!=null){bool shown=caption.Visible;runtime.Activate("captions");CheckResult("caption_toggle_uses_real_component",caption.Visible!=shown);runtime.Activate("captions");}
   runtime.Activate("tab1");yield return null;camera.transform.position=position+new Vector3(.21f,.10f,-.84f);camera.transform.LookAt(position);Save(camera,output,"02-placement-angle.png");
   runtime.Activate("tab2");yield return null;camera.transform.position=position+new Vector3(-.12f,.04f,-.82f);camera.transform.LookAt(position);Save(camera,output,"03-size-angle.png");
   var character=FindAnyObjectByType<SiCharacterController>();var originalPosition=character.PlanarPosition;float originalYaw=character.Yaw,scale=character.CharacterScale,ground=character.GroundHeight;
   runtime.Activate("larger");CheckResult("size_control_updates_current_character",character.CharacterScale>scale);character.RestoreRoomPlacement(originalPosition,originalYaw,scale,ground);
   var controller=FindAnyObjectByType<ControllerHands>();if(controller!=null&&controller.Ball!=null){bool kinematic=controller.Ball.isKinematic;controller.Ball.isKinematic=true;var skins=FindAnyObjectByType<SiSkinSwitcher>();string id=skins.CurrentId;runtime.Activate("skin");CheckResult("held_object_blocks_skin_change",skins.CurrentId==id);
    int actions=runtime.Activations;ReplayPress(runtime,"close");CheckResult("held_ball_approach_neither_activates_nor_releases",runtime.Activations==actions&&controller.Ball.isKinematic&&runtime.Open);controller.Ball.isKinematic=kinematic;
   }
   runtime.Activate("tab0");int beforeTouch=runtime.Activations;bool beforeMute=auto.Muted;ReplayPress(runtime,"voice");CheckResult("native_pointer_replay_reaches_real_toggle_once",runtime.Activations==beforeTouch+1&&auto.Muted!=beforeMute);runtime.Activate("voice");
   int beforeFast=runtime.Activations;bool fastMute=auto.Muted;ReplayFastPoke(runtime,"voice");CheckResult("visible_pose_fast_partial_hand_poke_toggles_once_despite_physics_lag",runtime.Activations==beforeFast+1&&auto.Muted!=fastMute);runtime.Activate("voice");
   CheckResult("panel_remains_world_fixed",Vector3.Distance(runtime.View.Panel.position,anchored)<.00001f);
   runtime.Close();yield return new WaitForSeconds(.45f);CheckResult("touch_close_animation_completes",!runtime.View.Visible);CheckResult("subtitles_restore_after_panel_close",!runtime.CaptionsSuppressed&&caption!=null&&caption.Visible);
   runtime.ReviewOpen(position,rotation);yield return new WaitForSeconds(.11f);Save(camera,output,"04-summon-in-progress.png");CheckResult("summon_has_animated_depth",runtime.View.Reveal>0&&runtime.View.Reveal<1);
   var result=new Result{pass=true,checks=checks.ToArray()};foreach(var check in checks)result.pass&=check.pass;
   using(var stream=new FileStream(Path.Combine(output,"result.json"),FileMode.CreateNew))using(var writer=new StreamWriter(stream))writer.Write(JsonUtility.ToJson(result,true));Debug.Log("MGFR_HAND_MENU_REVIEW_"+(result.pass?"PASS":"FAIL"));Application.Quit(result.pass?0:5);
  }
  static void ReplayFastPoke(GesturePanelRuntime runtime,string key){
   var control=runtime.View.Controls.Find(item=>item.key==key);float now=Time.unscaledTime;
   foreach(float z in new[]{-.052f,-.030f,.025f,.07f,.07f}){
    var target=runtime.View.Panel.TransformPoint(new Vector3(control.rect.center.x,control.rect.center.y,z));var frame=Fixture(now,false);
    var offset=target-frame.Joints[10].position;for(int j=0;j<26;j++)frame.Joints[j]=new Pose(frame.Joints[j].position+offset,frame.Joints[j].rotation);
    foreach(int j in new[]{15,20,25})frame.Observed[j]=false;
    var stable=Fixture(now,false);var stableTarget=runtime.View.Panel.TransformPoint(new Vector3(control.rect.center.x,control.rect.center.y,-.12f));var lag=stableTarget-stable.Joints[10].position;
    for(int j=0;j<26;j++)stable.Joints[j]=new Pose(stable.Joints[j].position+lag,stable.Joints[j].rotation);
    runtime.ReviewVisibleTouch(frame,stable,0,now);now+=1f/72;
   }
  }
  static void ReplayPress(GesturePanelRuntime runtime,string key){
   var control=runtime.View.Controls.Find(item=>item.key==key);float now=Time.unscaledTime;
   for(int i=0;i<80;i++){
    float z=i<20?-.12f:GesturePanelVisual.SurfaceZ;var target=runtime.View.Panel.TransformPoint(new Vector3(control.rect.center.x,control.rect.center.y,z));
    var frame=Fixture(now,false);var offset=target-frame.Joints[10].position;for(int j=0;j<26;j++)frame.Joints[j]=new Pose(frame.Joints[j].position+offset,frame.Joints[j].rotation);
    runtime.ReviewTouch(frame,0,now);now+=.01f;
   }
  }
  static void Save(Camera camera,string directory,string name){
   if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-hand-menu-no-capture")>=0)return;
   PanelLabel.FlushAll();
   var target=new RenderTexture(1400,1000,24,RenderTextureFormat.ARGB32){antiAliasing=1};target.Create();camera.targetTexture=target;camera.aspect=1.4f;camera.Render();var previous=RenderTexture.active;RenderTexture.active=target;var image=new Texture2D(1400,1000,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1400,1000),0,0);image.Apply();using(var stream=new FileStream(Path.Combine(directory,name),FileMode.CreateNew)){var data=image.EncodeToPNG();stream.Write(data,0,data.Length);}RenderTexture.active=previous;camera.targetTexture=null;target.Release();Destroy(image);Destroy(target);
  }
 }
}
