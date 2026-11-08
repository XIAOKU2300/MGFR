from pathlib import Path
import shutil

lab=Path('H:/MGFR/HandLab-20261018');old=lab/'Project-v8';project=lab/'Project-v9';source=lab/'Sources/v9';source.mkdir()
changes={}
path=Path('Assets/MGFR/Scripts/BareHands/HandJointSource.cs');text=(old/path).read_text(encoding='utf8')
text=text.replace('public bool Replay {get;set;}','public readonly HandFrame[] RenderFrames={new HandFrame(),new HandFrame()};\n  public bool Replay {get;set;}')
text=text.replace('{Frames[h].Clear();filters[h].Reset();}','{Frames[h].Clear();RenderFrames[h].Clear();filters[h].Reset();}')
text=text.replace('if(!hand.isTracked){f.Clear();filters[h].Reset();return;}','if(!hand.isTracked){f.Clear();RenderFrames[h].Clear();filters[h].Reset();return;}')
text=text.replace('filters[h].Process(raw,f,Time.realtimeSinceStartupAsDouble);','filters[h].Process(raw,f,Time.realtimeSinceStartupAsDouble);\n   UpdateRenderFrame(h,raw,f);')
text=text.replace('   if(!tracked)return;','   if(!tracked){RenderFrames[hand].Clear();return;}')
text=text.replace('for(int i=0;i<26;i++)f.Observed[i]=true;','for(int i=0;i<26;i++)f.Observed[i]=true;\n   UpdateRenderFrame(hand,f,f);')
marker='  public void SetReplayFrame'
method='''  // Visual occlusion follows the freshest SDK sample, independent of physics smoothing and size gain.
  public void UpdateRenderFrame(int h,HandFrame observed,HandFrame stable)
  {
   var target=RenderFrames[h];target.Clear();target.Timestamp=observed.Timestamp;
   if(!observed.Valid[1])return;
   var wrist=observed.Joints[1];var inverse=Quaternion.Inverse(stable.Joints[1].rotation);
   for(int i=0;i<26;i++)
   {
    if(observed.Valid[i])
    {
     target.Joints[i]=observed.Joints[i];target.Radius[i]=observed.Radius[i];target.Observed[i]=true;target.ObservedCount++;
    }
    else if(stable.Valid[i])
    {
     var relative=inverse*(stable.Joints[i].position-stable.Joints[1].position)/HandPoseStabilizer.SizeGain;
     target.Joints[i]=new Pose(wrist.position+wrist.rotation*relative,wrist.rotation*inverse*stable.Joints[i].rotation);
     target.Radius[i]=stable.Radius[i]/HandPoseStabilizer.SizeGain;
    }
    else continue;
    target.Valid[i]=true;target.ValidCount++;
   }
   target.Tracked=target.ValidCount>=20&&target.Valid[0]&&target.Valid[1]&&target.Valid[7]&&target.Valid[12]&&target.Valid[17]&&target.Valid[22];
  }
'''
assert marker in text;text=text.replace(marker,method+marker);changes[path]=text

path=Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs');text=(old/path).read_text(encoding='utf8')
text=text.replace('DepthMeshes[h].Update(f,tracked&&OcclusionEnabled);','DepthMeshes[h].Update(Source.RenderFrames[h],tracked&&OcclusionEnabled);')
text=text.replace('DepthMeshes[h].Update(Source.Frames[h],PreferBareHands&&OcclusionEnabled);','DepthMeshes[h].Update(Source.RenderFrames[h],PreferBareHands&&OcclusionEnabled);')
changes[path]=text

path=Path('Assets/MGFR/Scripts/BareHands/HandDepthMesh.cs');text=(old/path).read_text(encoding='utf8')
text=text.replace(')*1.04f;',');').replace('rawJointPositions=True calibration=False','renderPose=latestSDK physicsPose=stabilized depthInset=1.5mm calibration=False')
changes[path]=text

path=Path('Assets/MGFR/Resources/HandDepth.shader');text=(old/path).read_text(encoding='utf8')
text=text.replace('float4 _Tint;','float4 _Tint;float _WriteColor;')
text=text.replace('o.pos=UnityObjectToClipPos(v.vertex);o.normal=UnityObjectToWorldNormal(v.normal);return o;', '''o.normal=UnityObjectToWorldNormal(v.normal);
    float3 world=mul(unity_ObjectToWorld,v.vertex).xyz;
    if(_WriteColor<1)world-=normalize(o.normal)*.0015;
    o.pos=mul(UNITY_MATRIX_VP,float4(world,1));return o;''')
changes[path]=text

for folder in ('Assets','Packages','ProjectSettings'):
 def ignore(path,names):return [name for name in names if (Path(path)/name).relative_to(old) in changes]
 shutil.copytree(old/folder,project/folder,ignore=ignore)
for relative,text in changes.items():
 with (source/relative.name).open('x',encoding='utf8') as file:file.write(text)
 with (project/relative).open('x',encoding='utf8') as file:file.write(text)
print(project)
