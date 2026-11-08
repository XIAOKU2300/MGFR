from pathlib import Path
import hashlib, json, shutil

lab=Path(__file__).resolve().parent
base=lab.parent/'ControllerRoom-20261019/Project2'
project=lab/'Project'
assert not project.exists()
changes={}
def once(s,a,b):
    assert s.count(a)==1,a[:100]
    return s.replace(a,b)
def read(p):return (base/p).read_text(encoding='utf-8-sig')
p=Path('Assets/MGFR/Scripts/BareHands/HandJointSource.cs');s=read(p)
s=once(s,'  public bool ControllerDriven {get;set;}', '''  // Native samples and render poses remain live regardless of interaction source.
  public readonly HandFrame[] NativeFrames={new HandFrame(),new HandFrame()};
  readonly bool[] controllerPose=new bool[2];
  public bool ControllerDriven=>controllerPose[0]||controllerPose[1];
  public bool IsControllerPose(int hand)=>controllerPose[hand];
  public string InputLabel(int hand)=>controllerPose[hand]?"CONTROLLER":"NATIVE";
  public bool HasFreshNativePose(int hand)=>NativeFrames[hand].Tracked&&Time.unscaledTime-NativeFrames[hand].Timestamp<=.1f;
  public void UseControllerPose(int hand,bool value)
  {
   if(controllerPose[hand]==value)return;controllerPose[hand]=value;
   if(!value&&HasFreshNativePose(hand))CopyFrame(NativeFrames[hand],Frames[hand]);else Frames[hand].Clear();
  }
  static void CopyFrame(HandFrame from,HandFrame to)
  {
   to.Tracked=from.Tracked;to.ValidCount=from.ValidCount;to.ObservedCount=from.ObservedCount;to.Timestamp=from.Timestamp;
   Array.Copy(from.Joints,to.Joints,26);Array.Copy(from.Radius,to.Radius,26);
   Array.Copy(from.Valid,to.Valid,26);Array.Copy(from.Observed,to.Observed,26);
  }''')
assert s.count('if(Replay||ControllerDriven)return;')==2
s=s.replace('if(Replay||ControllerDriven)return;','if(Replay)return;')
s=once(s,'    if(!Running||Time.unscaledTime-Frames[h].Timestamp>.1f){Frames[h].Clear();filters[h].Reset();}',
'''    if(!Running||Time.unscaledTime-NativeFrames[h].Timestamp>.1f)
    {NativeFrames[h].Clear();filters[h].Reset();if(!controllerPose[h])Frames[h].Clear();}''')
for h in (0,1):
    s=once(s,f'Read({h},s.{"leftHand" if h==0 else "rightHand"},Frames[{h}],',f'Read({h},s.{"leftHand" if h==0 else "rightHand"},NativeFrames[{h}],')
s=once(s,'f.Clear();RenderFrames[h].Clear();return;}', 'f.Clear();RenderFrames[h].Clear();filters[h].Reset();if(!controllerPose[h])Frames[h].Clear();return;}')
s=once(s,'   if(type==XRHandSubsystem.UpdateType.Dynamic){filters[h].Process(sample,Frames[h],now);PhysicsSamples++;}\n   UpdateRenderFrame(h,sample,Frames[h]);',
'''   if(type==XRHandSubsystem.UpdateType.Dynamic)
   {filters[h].Process(sample,NativeFrames[h],now);if(!controllerPose[h])CopyFrame(NativeFrames[h],Frames[h]);PhysicsSamples++;}
   UpdateRenderFrame(h,sample,NativeFrames[h]);''')
s=once(s,'   ControllerDriven=true;var f=Frames[hand];f.Clear();f.Timestamp=Time.unscaledTime;',
           '   UseControllerPose(hand,true);var f=Frames[hand];f.Clear();f.Timestamp=Time.unscaledTime;')
s=once(s,'   if(!tracked||joints==null){RenderFrames[hand].Clear();return;}', '   if(!tracked||joints==null)return;')
s=once(s,'   // These joints are an explicit controller grip proxy, not measured fingers.\n   // The source flag also disables real-hand occlusion for this pose source.',
           '   // Interaction proxy only. Never overwrite native joints or their render pose.')
s=once(s,'   f.Tracked=true;f.ValidCount=f.ObservedCount=26;UpdateRenderFrame(hand,f,f);',
           '   f.Tracked=true;f.ValidCount=f.ObservedCount=26;')
s=once(s,'   Replay=true;var f=Frames[hand];', '   Replay=true;UseControllerPose(hand,false);var f=Frames[hand];')
changes[p]=s
p=Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs');s=read(p)
s=once(s,'   if(Source.Replay||!Source.Running||!tracked)DepthMeshes[h].Update(Source.RenderFrames[h],tracked&&OcclusionEnabled&&!Source.ControllerDriven);',
'''   if(Source.Replay||!Source.Running||!Source.RenderFrames[h].Tracked||Source.IsControllerPose(h))
    DepthMeshes[h].Update(Source.RenderFrames[h],OcclusionEnabled);''')
s=once(s,'PreferBareHands&&OcclusionEnabled&&!Source.ControllerDriven);','OcclusionEnabled);')
s=once(s,'Source.ControllerDriven?"CONTROLLER_GRIP":Source.Replay?"TEST_REPLAY":"XR_RUNTIME"',
           'Source.ControllerDriven?"PER_HAND":Source.Replay?"TEST_REPLAY":"XR_RUNTIME"')
s=once(s,'source={(Source.ControllerDriven?', 'leftSource={Source.InputLabel(0)} rightSource={Source.InputLabel(1)} source={(Source.ControllerDriven?')
s=once(s,'   GUILayout.Label(Source.Replay?"手部回放测试（非头显实测）":PreferBareHands?"徒手交互":"手柄交互");',
'''   GUILayout.Label(Source.Replay?"手部回放测试（非头显实测）":$"手部交互 左:{Source.InputLabel(0)} 右:{Source.InputLabel(1)} · 真实手部透视保留");''')
changes[p]=s
p=Path('Assets/MGFR/Wardrobe/WardrobeLiveRuntime.cs');s=read(p)
s=once(s,'        public void SetInteractionEnabled(bool value)', '''        public void CancelInputHand(int h)
        {if(h<0||h>1)return;Cancel(h);pinches[h].Reset();state[h].blocked=true;}
        public void SetInteractionEnabled(bool value)''');changes[p]=s
p=Path('Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs');s=read(p)
s=once(s,'a=="-mgfr-controller-review"','a=="-mgfr-coexist-review"||a=="-mgfr-controller-review"');changes[p]=s
p=Path('Assets/MGFR/Scripts/Character/ControllerGripSource.cs');changes[p]=(lab/'Source/ControllerGripSource.cs').read_text(encoding='utf-8')
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(base) in changes]
for name in ('Assets','Packages','ProjectSettings'):shutil.copytree(base/name,project/name,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
for p in (lab/'Source').glob('*.cs'):
    if p.name=='ControllerGripSource.cs':continue
    target=project/'Assets/MGFR/Scripts/Character'/p.name
    assert not target.exists();shutil.copyfile(p,target)
with (lab/'base-hashes.json').open('x',encoding='utf-8') as f:
    json.dump({p.as_posix():hashlib.sha256((base/p).read_bytes()).hexdigest() for p in changes},f,indent=2)
with (lab/'desktop-no-runtime.json').open('x') as f:f.write('{}\n')
print(project)
