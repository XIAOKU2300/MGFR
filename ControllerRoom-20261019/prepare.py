from pathlib import Path
import difflib, hashlib, json, shutil

lab=Path(__file__).resolve().parent
base=lab.parent/'FloorPlacement-20261019/Project'
project=lab/'Project'
assert not project.exists()
changes={}
def once(s,a,b):
    assert s.count(a)==1,a[:100]
    return s.replace(a,b)
def read(p):return (base/p).read_text(encoding='utf-8-sig')

p=Path('Assets/MGFR/Scripts/Character/SiCharacterController.cs');s=read(p)
s=once(s,'        void ApplyPlacement()','''        public void AdjustRoomPlacement(Vector3 movement, float yaw, float scale, float ground)
        {
            if (!float.IsFinite(movement.sqrMagnitude) || !float.IsFinite(yaw) || !float.IsFinite(scale) || !float.IsFinite(ground)) return;
            PlanarPosition += movement;
            Yaw = Mathf.Repeat(Yaw + yaw, 360f);
            CharacterScale = Mathf.Clamp(CharacterScale + scale, minScale, maxScale);
            GroundHeight = Mathf.Clamp(GroundHeight + ground, minGroundHeight, maxGroundHeight);
            LastAction = "controller placement"; ApplyPlacement();
        }
        public void RememberRoomPlacement()
        {
            defaultPosition = PlanarPosition; defaultYaw = Yaw;
            defaultScale = CharacterScale; defaultGroundHeight = GroundHeight;
        }
        public void RestoreRoomPlacement(Vector3 position, float yaw, float scale, float ground)
        {
            if (!float.IsFinite(position.sqrMagnitude) || !float.IsFinite(yaw) || !float.IsFinite(scale) || !float.IsFinite(ground)) return;
            PlanarPosition = position; Yaw = yaw;
            CharacterScale = scale; GroundHeight = ground; ApplyPlacement();
        }

        void ApplyPlacement()''');changes[p]=s
p=Path('Assets/MGFR/Scripts/Character/RoomFloorPlacement.cs');s=read(p)
s=once(s,'        public float Distance = 1.5f;','''        public float Distance = 1.5f;
        public bool ControllerShortcutBlocked;
        public int AnchorRevision { get; private set; }''')
s=once(s,'            bool held = left.isValid','            bool held = !ControllerShortcutBlocked && left.isValid')
s=once(s,'            character.PlaceOnGround(headPosition, forward, Distance, ground);','''            AnchorRevision++;
            character.PlaceOnGround(headPosition, forward, Distance, ground);''');changes[p]=s
p=Path('Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs');s=read(p)
s=once(s,'a=="-mgfr-floor-review"','a=="-mgfr-controller-review"||a=="-mgfr-floor-review"')
s=once(s,'  void StopCapture()','  public void SetMuted(bool value){Muted=value;}\n  void StopCapture()');changes[p]=s
p=Path('Assets/MGFR/Scripts/Dialogue/CameraChatOverlay.cs');s=read(p)
s=once(s,'  public string DisplayedUser=>user;', '  public bool Visible=>shown;\n  public string DisplayedUser=>user;');changes[p]=s
p=Path('Assets/MGFR/Wardrobe/WardrobeLiveRuntime.cs');s=read(p)
s=once(s,'            Enabled=!Enabled;CancelHands();Status=Enabled?"穿脱已开启":"穿脱已关闭，布料捏拉保留";',
'            SetInteractionEnabled(!Enabled);')
s=once(s,'        public void ResetAll()', '''        public void SetInteractionEnabled(bool value)
        {Enabled=value;CancelHands();Status=Enabled?"穿脱已开启":"穿脱已关闭，布料捏拉保留";}
        public void ResetAll()''');changes[p]=s
p=Path('Assets/MGFR/Scripts/BareHands/HandJointSource.cs');s=read(p)
s=once(s,'  public bool Replay {get;set;}','''  public bool Replay {get;set;}
  public bool ControllerDriven {get;set;}''')
assert s.count('if(Replay)return;')==2
s=s.replace('if(Replay)return;','if(Replay||ControllerDriven)return;')
s=once(s,'  public void SetReplayFrame(int hand,Pose[] joints,bool tracked)', '''  public void PublishControllerFrame(int hand,Pose[] joints,bool tracked)
  {
   ControllerDriven=true;var f=Frames[hand];f.Clear();f.Timestamp=Time.unscaledTime;
   if(!tracked||joints==null){RenderFrames[hand].Clear();return;}
   // These joints are an explicit controller grip proxy, not measured fingers.
   // The source flag also disables real-hand occlusion for this pose source.
   for(int i=0;i<26;i++)
   {f.Joints[i]=joints[i];f.Radius[i]=i<2?.018f:.008f;f.Valid[i]=f.Observed[i]=true;}
   f.Tracked=true;f.ValidCount=f.ObservedCount=26;UpdateRenderFrame(hand,f,f);
  }
  public void SetReplayFrame(int hand,Pose[] joints,bool tracked)''');changes[p]=s
p=Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs');s=read(p)
s=once(s,'   if(Input.GetKeyDown(KeyCode.F9)){PreferBareHands=!PreferBareHands;Release(0);Release(1);}', '''   if(Input.GetKeyDown(KeyCode.F9))
   {
    if(MGFR.Character.ControllerGripSource.Instance!=null)MGFR.Character.ControllerGripSource.Instance.CycleMode();
    else {PreferBareHands=!PreferBareHands;Release(0);Release(1);}
   }''')
s=once(s,'tracked&&OcclusionEnabled);','tracked&&OcclusionEnabled&&!Source.ControllerDriven);')
s=once(s,'PreferBareHands&&OcclusionEnabled);','PreferBareHands&&OcclusionEnabled&&!Source.ControllerDriven);')
s=once(s,'Source.Replay?"TEST_REPLAY":"XR_RUNTIME"','Source.ControllerDriven?"CONTROLLER_GRIP":Source.Replay?"TEST_REPLAY":"XR_RUNTIME"');changes[p]=s
p=Path('Assets/MGFR/Scripts/Experience/ControllerHands.cs');s=read(p)
for line in ('                            device.TryGetFeatureValue(CommonUsages.primary2DAxis,out Vector2 stick);\n',
             '                            hand.Offset+=new Vector3(stick.x,0,stick.y)*Time.deltaTime*.25f;\n',
             '                            hand.Offset=Vector3.ClampMagnitude(hand.Offset,.35f);\n'):
    s=once(s,line,'')
s=once(s,'Hands: controllers + stick offset / grip or trigger to grab','Hands: controllers / grip or trigger to grab; Y opens quick menu');changes[p]=s

def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(base) in changes]
for name in ('Assets','Packages','ProjectSettings'):shutil.copytree(base/name,project/name,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
for p in (lab/'Source').glob('*.cs'):
    s=p.read_text(encoding='utf-8')
    if p.name=='ControllerGripSource.cs':
        s=once(s,'            bool tracked = TrackedController(device) &&','''            Vector3 position = Vector3.zero; Quaternion rotation = Quaternion.identity;
            bool tracked = TrackedController(device) &&''')
        s=once(s,'out Vector3 position)','out position)')
        s=once(s,'out Quaternion rotation);','out rotation);')
    if p.name=='ControllerActions.cs':
        s=once(s,'        bool neutralRequired, navHeld;','        bool neutralRequired, navHeld; int savedRevision;')
        s=once(s,'            if (back)','''            if (Placing && floor != null && floor.AnchorRevision != savedRevision)
            { Placing = MenuOpen = false; Say("地面已重新标定，已更新摆放位置"); return; }
            if (back)''')
        s=once(s,'                        Placing = true;','                        Placing = true; savedRevision = floor != null ? floor.AnchorRevision : 0;')
    target=project/'Assets/MGFR/Scripts/Character'/p.name
    assert not target.exists()
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
hashes={p.as_posix():hashlib.sha256((base/p).read_bytes()).hexdigest() for p in changes}
with (lab/'base-hashes.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2)
with (lab/'desktop-no-runtime.json').open('x') as f:f.write('{}\n')
print(project)
