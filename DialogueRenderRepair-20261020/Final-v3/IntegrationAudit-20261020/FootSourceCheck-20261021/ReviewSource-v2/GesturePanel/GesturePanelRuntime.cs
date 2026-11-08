using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Character;
using MGFR.BareHands;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Skins;
using MGFR.Skins.ClothPhysics;
using MGFR.Wardrobe;

namespace MGFR.GesturePanel {
 [DefaultExecutionOrder(1200)] public sealed class GesturePanelRuntime:MonoBehaviour {
  public bool Ready {get;private set;}public bool Open {get;private set;}public int Summons {get;private set;}public int Activations {get;private set;}
  public GesturePanelVisual View {get;private set;}public bool ManualReview;public string LastAction {get;private set;}="";
  readonly FistSummonGate[] summon={new FistSummonGate(),new FistSummonGate()};
  readonly FingerTouchGate[] touch={new FingerTouchGate(),new FingerTouchGate()};
  readonly bool[] owns={false,false};
  BareHandInteraction hands;SiSkinSwitcher skins;SiCharacterController character;ControllerActions oldMenu;ControllerHands controllers;RoomFloorPlacement floor;WardrobeLiveRuntime wardrobe;SwimsuitClothRuntime cloth;AutomaticVoiceSession voice;CameraChatOverlay captions;
  AssetBundle bundle;Func<int,bool> previousOwnership,ownership;int page,summonHand,lastContacts;float contactUntil,openedAt,lastUse,nextStatus;bool touchReady;string signature="";
  readonly List<Renderer> detached=new List<Renderer>();float nextDetached;
  readonly Dictionary<Renderer,bool> captionSuppression=new Dictionary<Renderer,bool>();
  public bool CaptionsSuppressed=>View!=null&&View.Visible&&captionSuppression.Count>0;
  static bool Has(string flag)=>Array.IndexOf(Environment.GetCommandLineArgs(),flag)>=0;
  public static void Install(){
   if(FindAnyObjectByType<GesturePanelRuntime>()!=null)return;
   var panel=new GameObject("Fist-summoned spatial controls").AddComponent<GesturePanelRuntime>();
   if(Has("-mgfr-hand-menu-review")){panel.ManualReview=true;new GameObject("Hand menu verification").AddComponent<GesturePanelReview>();}
  }
  IEnumerator Start(){
   if(ManualReview){AudioListener.volume=0;var automatic=FindAnyObjectByType<AutomaticVoiceSession>();if(automatic!=null)automatic.enabled=false;}
   while((hands=FindAnyObjectByType<BareHandInteraction>())==null||!hands.IsReady||hands.Source==null||(skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady)yield return null;
   character=FindAnyObjectByType<SiCharacterController>();oldMenu=FindAnyObjectByType<ControllerActions>();controllers=FindAnyObjectByType<ControllerHands>();floor=FindAnyObjectByType<RoomFloorPlacement>();wardrobe=FindAnyObjectByType<WardrobeLiveRuntime>();cloth=FindAnyObjectByType<SwimsuitClothRuntime>();voice=FindAnyObjectByType<AutomaticVoiceSession>();captions=FindAnyObjectByType<CameraChatOverlay>();
   if(oldMenu!=null){oldMenu.Manual=true;oldMenu.enabled=false;if(oldMenu.View!=null){oldMenu.View.Hide();oldMenu.View.enabled=false;}}
   if(floor!=null)floor.ControllerShortcutBlocked=true;
   bundle=AssetBundle.LoadFromFile(Path.Combine(Application.streamingAssetsPath,"gesture-touch-panel-v1"));if(bundle==null)throw new InvalidOperationException("Gesture panel shader bundle missing");
   var surface=bundle.LoadAsset<Shader>("Assets/GesturePanel.shader");var text=bundle.LoadAsset<Shader>("Assets/GesturePanelText.shader");
   if(surface==null||text==null||!surface.isSupported||!text.isSupported)throw new InvalidOperationException("Gesture panel shader unsupported");
   View=gameObject.AddComponent<GesturePanelVisual>();View.Initialize(surface,text);ownership=OwnsHand;InstallOwnership();Ready=true;BuildPage();Debug.Log("MGFR_HAND_PANEL_READY nativeOnly=True holdSeconds=3 worldFixed=True directTouch=True");
  }
  void InstallOwnership(){if(hands.ExternalClothGrab!=ownership){previousOwnership=hands.ExternalClothGrab;hands.ExternalClothGrab=ownership;}}
  public bool OwnsHand(int h)=>owns[h]||(previousOwnership!=null&&previousOwnership(h));
  public bool AnyHolding(){
   if(hands==null)return false;
   for(int h=0;h<2;h++)if(hands.GrabbedBody[h]>=0||(wardrobe!=null&&wardrobe.OwnsHand(h))||(cloth!=null&&cloth.Solver!=null&&cloth.Solver.Grips[h].particle>=0))return true;
   return controllers!=null&&controllers.Ball!=null&&controllers.Ball.isKinematic;
  }
  bool Held(int h)=>hands.GrabbedBody[h]>=0||(wardrobe!=null&&wardrobe.OwnsHand(h))||(cloth!=null&&cloth.Solver!=null&&cloth.Solver.Grips[h].particle>=0);
  bool BallHeld=>controllers!=null&&controllers.Ball!=null&&controllers.Ball.isKinematic;
  bool NearCharacter(HandFrame f){
   if(f==null||!f.Tracked)return false;var bounds=skins.Loader.Renderer.bounds;
   foreach(int j in new[]{0,1,5,10,15,20,25})if(f.Valid[j]){
    var point=f.Joints[j].position;if(bounds.SqrDistance(point)<.18f*.18f)return true;
    if(controllers!=null&&controllers.Ball!=null&&Vector3.Distance(point,controllers.Ball.position)<.18f)return true;
    foreach(var renderer in detached)if(renderer!=null&&renderer.bounds.SqrDistance(point)<.14f*.14f)return true;
   }return false;
  }
  void ApplyCaptionOcclusion(){
   bool suppress=View!=null&&View.Visible;
   if(suppress&&captions!=null)foreach(var renderer in captions.GetComponentsInChildren<Renderer>(true)){
    if(!captionSuppression.ContainsKey(renderer))captionSuppression.Add(renderer,renderer.forceRenderingOff);renderer.forceRenderingOff=true;
   }
   if(!suppress){foreach(var item in captionSuppression)if(item.Key!=null)item.Key.forceRenderingOff=item.Value;captionSuppression.Clear();}
  }
  void LateUpdate(){if(!Ready)return;InstallOwnership();ApplyCaptionOcclusion();if(oldMenu!=null&&oldMenu.View!=null)oldMenu.View.Hide();if(ManualReview)return;
   float now=Time.unscaledTime;
   if(now>=nextDetached){nextDetached=now+.5f;detached.Clear();foreach(var renderer in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))if(renderer.name.EndsWith(" detached",StringComparison.Ordinal))detached.Add(renderer);}
   if(hands.FingerContacts!=lastContacts){lastContacts=hands.FingerContacts;contactUntil=now+.55f;}
   bool blocked=AnyHolding()||now<contactUntil||NearCharacter(hands.Source.NativeFrames[0])||NearCharacter(hands.Source.NativeFrames[1]);
   int fired=-1;for(int h=0;h<2;h++)if(summon[h].Step(hands.Source.NativeFrames[h],now,!hands.Source.IsControllerPose(h),blocked,Open))fired=h;
   if(fired>=0)SummonAt(fired,hands.Source.NativeFrames[fired].Joints[0].position);
   if(!Open){int leading=summon[1].Progress>summon[0].Progress?1:0;var f=hands.Source.NativeFrames[leading];if(f.Tracked&&Camera.main!=null)View.ShowProgress(f.Joints[0].position+Vector3.up*.11f,Quaternion.LookRotation(f.Joints[0].position-Camera.main.transform.position,Vector3.up),summon[leading].Progress);else View.ShowProgress(Vector3.zero,Quaternion.identity,0);owns[0]=owns[1]=false;return;}
   UpdateTouchRelease(hands.Source.RenderFrames[summonHand],now,!hands.Source.IsControllerPose(summonHand));
   int hover=-1;float compression=0;
   for(int h=0;h<2;h++){
    // Use the same fresh SDK pose as the visible hand, without physics smoothing.
    int action=ReadCurrentTouch(h,now);
    if(touch[h].Hovered>=0){hover=touch[h].Hovered;compression=Mathf.Max(compression,touch[h].Compression);lastUse=now;}
    if(action>=0){Activate(View.Controls[action].key);hover=-1;break;}
   }
   View.PresentTouch(hover,compression);
   if(Camera.main!=null&&Vector3.Distance(Camera.main.transform.position,View.Panel.position)>1.8f||now-lastUse>60)Close();
   if(now>=nextStatus){nextStatus=now+.35f;string state=StateSignature();if(state!=signature)BuildPage();}
  }
  void UpdateTouchRelease(HandFrame frame,float now,bool native){
   if(!touchReady&&native&&HandMenuPose.FreshTouch(frame,now)&&HandMenuPose.Pointer(frame)){
    touchReady=true;View.SetFeedback("食指碰到即触发；退指后可再次点击");
   }
  }
  int ReadCurrentTouch(int hand,float now)=>ReadTouch(hands.Source.RenderFrames[hand],hand,now);
  int ReadTouch(HandFrame frame,int h,float now){
   // Open-panel contact takes priority near an enlarged character. Existing
   // grabs, including the private ball owner, must never be canceled by the UI.
   bool valid=touchReady&&View.Settled&&HandMenuPose.FreshTouch(frame,now)&&!hands.Source.IsControllerPose(h)&&HandMenuPose.Pointer(frame)&&!Held(h)&&!BallHeld;
   Vector3 point=valid?View.Panel.InverseTransformPoint(frame.Joints[10].position):Vector3.zero;
   int hit=valid?View.Hit(touch[h].ContactPoint(point,frame.Radius[10],GesturePanelVisual.SurfaceZ,frame.Timestamp)):-1;
   owns[h]=valid&&Mathf.Abs(point.x)<.36f&&Mathf.Abs(point.y)<.25f&&point.z>-.14f&&point.z<.16f;
   if(owns[h])hands.CancelForWardrobe(h);
   return touch[h].Step(valid,frame.Timestamp,point,frame.Radius[10],hit,GesturePanelVisual.SurfaceZ,now,hit>=0?View.Controls[hit].hold:0);
  }
  void SummonAt(int hand,Vector3 palm){
   if(Camera.main==null)return;var head=Camera.main.transform;var target=palm+Vector3.up*.32f;var flat=Vector3.ProjectOnPlane(target-head.position,Vector3.up);if(flat.sqrMagnitude<.01f)flat=Vector3.ProjectOnPlane(head.forward,Vector3.up);flat.Normalize();
   float horizontal=Vector3.ProjectOnPlane(target-head.position,Vector3.up).magnitude;if(horizontal<.46f)target+=flat*(.46f-horizontal);if(horizontal>.65f)target-=flat*(horizontal-.65f);
   target.y=Mathf.Clamp(target.y,head.position.y-.30f,head.position.y+.12f);
   OpenAt(target,Quaternion.LookRotation((target-head.position).normalized,Vector3.up),hand);
  }
  void OpenAt(Vector3 position,Quaternion rotation,int hand){
   Open=true;Summons++;summonHand=hand;touchReady=false;openedAt=lastUse=Time.unscaledTime;page=0;
   for(int h=0;h<2;h++){summon[h].Closed(Time.unscaledTime);touch[h].Reset();owns[h]=false;}
   View.Show(position,rotation);ApplyCaptionOcclusion();BuildPage();
  }
  public void Close(){Open=false;View.Hide();for(int h=0;h<2;h++){owns[h]=false;touch[h].Reset();summon[h].Closed(Time.unscaledTime);}touchReady=false;}
  string StateSignature()=>page+":"+(voice!=null&&voice.Muted)+":"+(captions!=null&&captions.Visible)+":"+hands.Physics.Simulate+":"+(wardrobe!=null&&wardrobe.Enabled)+":"+skins.CurrentId+":"+skins.Style.Active+":"+Mathf.RoundToInt(character.CharacterScale*100);
  PanelControl Control(string key,string label,string detail,bool on=false,bool disabled=false,bool toggle=false)=>new PanelControl{key=key,label=label,detail=detail,on=on,disabled=disabled,toggle=toggle};
  public void BuildPage(){
   if(!Ready)return;signature=StateSignature();var controls=new List<PanelControl>();string[] titles={"常用开关","位置调整","大小与朝向"};
   for(int i=0;i<3;i++){var tab=Control("tab"+i,titles[i],"",page==i);tab.rect=new Rect(-.302f+i*.209f,.104f,.184f,.034f);controls.Add(tab);}
   PanelControl[] body;
   if(page==0)body=new[]{Control("voice","麦克风",voice==null?"尚未就绪":voice.Muted?"已静音":"已开启",voice!=null&&!voice.Muted,voice==null,true),Control("captions","对话字幕",captions!=null&&captions.Visible?"显示":"隐藏",captions!=null&&captions.Visible,captions==null,true),Control("physics","衣物物理",hands.Physics.Simulate?"自然运动":"暂停",hands.Physics.Simulate,false,true),Control("wardrobe","衣物穿脱",wardrobe!=null&&wardrobe.Enabled?"允许触碰与穿脱":"已关闭",wardrobe!=null&&wardrobe.Enabled,wardrobe==null,true),Control("skin","更换服装",skins.CurrentId=="swimsuit"?"当前：泳装":"当前：原服装"),Control("style","角色渲染",skins.Style.Active?"终末地风格":"原风格",skins.Style.Active,false,true)};
   else if(page==1)body=new[]{Control("left","向左移动","每次 8 厘米"),Control("right","向右移动","每次 8 厘米"),Control("near","靠近你","每次 8 厘米"),Control("far","远离你","每次 8 厘米"),Control("recenter","放到面前","按当前地面定位"),Control("save","保存位置","记住当前摆放")};
   else body=new[]{Control("smaller","缩小角色",Mathf.RoundToInt(character.CharacterScale*100)+"% · 衣物同比缩放",false,character.CharacterScale<=character.minScale+.001f),Control("larger","放大角色",Mathf.RoundToInt(character.CharacterScale*100)+"% · 衣物同比缩放",false,character.CharacterScale>=character.maxScale-.001f),Control("turnLeft","向左转","每次 15 度"),Control("turnRight","向右转","每次 15 度"),Control("lower","向下微调","每次 1 厘米"),Control("raise","向上微调","每次 1 厘米")};
   for(int i=0;i<body.Length;i++){body[i].rect=new Rect(i%2==0?-.292f:.015f,.0145f-(i/2)*.090f,.277f,.065f);controls.Add(body[i]);}
   var restore=Control("restore","长按恢复穿戴","");restore.hold=.35f;restore.rect=new Rect(-.292f,-.224f,.277f,.034f);controls.Add(restore);
   var ball=Control("ball","小球归位","");ball.rect=new Rect(.015f,-.224f,.277f,.034f);controls.Add(ball);
   var close=Control("close","收起","");close.rect=new Rect(.236f,.161f,.065f,.047f);controls.Add(close);
   View.SetControls(page,controls);for(int h=0;h<2;h++)touch[h].Reset();
  }
  public void Activate(string key){
   if(!Ready)return;LastAction=key;Activations++;lastUse=Time.unscaledTime;
   if(key.StartsWith("tab",StringComparison.Ordinal)){page=int.Parse(key.Substring(3));BuildPage();return;}
   if(key=="close"){Close();return;}
   if((key=="skin"||key=="restore"||key=="physics"||page>0)&&AnyHolding()){View.SetFeedback("请先松开手中的角色或衣物");return;}
   var camera=Camera.main;var forward=Vector3.ProjectOnPlane(camera!=null?camera.transform.forward:Vector3.forward,Vector3.up).normalized;var right=Vector3.Cross(Vector3.up,forward);
   switch(key){
    case "voice":voice?.SetMuted(!voice.Muted);break;
    case "captions":captions?.SetVisible(!captions.Visible);break;
    case "physics":hands.Physics.Simulate=!hands.Physics.Simulate;break;
    case "wardrobe":wardrobe?.SetInteractionEnabled(!wardrobe.Enabled);break;
    case "skin":skins.TrySelect(skins.CurrentId=="original"?"swimsuit":"original");break;
    case "style":skins.Style.SetActive(!skins.Style.Active);break;
    case "restore":wardrobe?.ResetAll();break;
    case "ball":controllers?.ResetBall();break;
    case "left":character.AdjustRoomPlacement(-right*.08f,0,0,0);break;
    case "right":character.AdjustRoomPlacement(right*.08f,0,0,0);break;
    case "near":character.AdjustRoomPlacement(-forward*.08f,0,0,0);break;
    case "far":character.AdjustRoomPlacement(forward*.08f,0,0,0);break;
    case "recenter":floor?.RequestPlacement();break;
    case "save":character.RememberRoomPlacement();break;
    case "smaller":character.AdjustRoomPlacement(Vector3.zero,0,-Mathf.Max(.05f,character.CharacterScale*.1f),0);break;
    case "larger":character.AdjustRoomPlacement(Vector3.zero,0,Mathf.Max(.05f,character.CharacterScale*.1f),0);break;
    case "turnLeft":character.AdjustRoomPlacement(Vector3.zero,-15,0,0);break;
    case "turnRight":character.AdjustRoomPlacement(Vector3.zero,15,0,0);break;
    case "lower":character.AdjustRoomPlacement(Vector3.zero,0,0,-.01f);break;
    case "raise":character.AdjustRoomPlacement(Vector3.zero,0,0,.01f);break;
   }
   BuildPage();View.SetFeedback(key=="save"?"已保存当前摆放":key=="restore"?"已恢复衣物和鞋子":"已更新；退指后可再次点击");
  }
  public void ReviewOpen(Vector3 position,Quaternion rotation){if(!Has("-mgfr-hand-menu-review"))throw new InvalidOperationException("Review flag required");OpenAt(position,rotation,0);touchReady=true;}
  public void ReviewTouch(HandFrame frame,int hand,float now){if(!Has("-mgfr-hand-menu-review"))throw new InvalidOperationException("Review flag required");int action=ReadTouch(frame,hand,now);if(action>=0)Activate(View.Controls[action].key);}
  public bool ReviewRelease(HandFrame frame,float now){if(!Has("-mgfr-hand-menu-review"))throw new InvalidOperationException("Review flag required");touchReady=false;UpdateTouchRelease(frame,now,true);return touchReady;}
  public void ReviewVisibleTouch(HandFrame visible,HandFrame stable,int hand,float now){
   if(!Has("-mgfr-hand-menu-review"))throw new InvalidOperationException("Review flag required");
   var oldVisible=hands.Source.RenderFrames[hand];var oldStable=hands.Source.NativeFrames[hand];
   try{hands.Source.RenderFrames[hand]=visible;hands.Source.NativeFrames[hand]=stable;int action=ReadCurrentTouch(hand,now);if(action>=0)Activate(View.Controls[action].key);}
   finally{hands.Source.RenderFrames[hand]=oldVisible;hands.Source.NativeFrames[hand]=oldStable;}
  }
  void OnDestroy(){foreach(var item in captionSuppression)if(item.Key!=null)item.Key.forceRenderingOff=item.Value;if(hands!=null&&hands.ExternalClothGrab==ownership)hands.ExternalClothGrab=previousOwnership;}
 }
}
