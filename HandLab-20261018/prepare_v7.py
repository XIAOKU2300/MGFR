from pathlib import Path
import shutil

lab=Path('H:/MGFR/HandLab-20261018');source=lab/'Sources/v7';project=lab/'Project-v7';old=lab/'Project-v6'
text=(old/'Assets/MGFR/Scripts/BareHands/HandJointSource.cs').read_text(encoding='utf8')
text=text.replace('public readonly bool[] Valid=new bool[26];','public readonly bool[] Valid=new bool[26];\n  public readonly bool[] Observed=new bool[26];public int ObservedCount;\n  public bool CanStartPinch=>Observed[5]&&Observed[10];')
text=text.replace('Tracked=false;ValidCount=0;Array.Clear(Valid,0,26);','Tracked=false;ValidCount=ObservedCount=0;Array.Clear(Valid,0,26);Array.Clear(Observed,0,26);')
text=text.replace('Transform origin;float nextScan;','Transform origin;float nextScan;\n  readonly HandPoseStabilizer[] filters={new HandPoseStabilizer(),new HandPoseStabilizer()};\n  readonly HandFrame raw=new HandFrame();')
text=text.replace('>.15f)Frames[h].Clear();','>.1f){Frames[h].Clear();filters[h].Reset();}')
text=text.replace('Read(s.leftHand,Frames[0],','Read(0,s.leftHand,Frames[0],').replace('Read(s.rightHand,Frames[1],','Read(1,s.rightHand,Frames[1],')
text=text.replace('void Read(XRHand hand,HandFrame f,bool updated)','void Read(int h,XRHand hand,HandFrame f,bool updated)')
text=text.replace('f.Clear();f.Timestamp=Time.unscaledTime;if(!hand.isTracked||!updated)return;','if(!hand.isTracked){f.Clear();filters[h].Reset();return;}\n   if(!updated)return;\n   raw.Clear();raw.Timestamp=Time.unscaledTime;')
start=text.index('   for(int i=0;i<26;i++)',text.index('void Read('));end=text.index('\n  public void SetReplayFrame',start)
block=text[start:end].replace('f.Joints','raw.Joints').replace('f.Valid','raw.Valid').replace('f.Radius','raw.Radius')
block=block[:block.index('   f.Tracked=')]+'   filters[h].Process(raw,f,Time.realtimeSinceStartupAsDouble);\n  }'
text=text[:start]+block+text[end:]
text=text.replace('f.Tracked=true;f.ValidCount=26;','f.Tracked=true;f.ValidCount=f.ObservedCount=26;for(int i=0;i<26;i++)f.Observed[i]=true;')
with (source/'HandJointSource.cs').open('x',encoding='utf8') as file:file.write(text)

text=(old/'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs').read_text(encoding='utf8')
text=text.replace('Pinching[h]=f.Valid[5]&&f.Valid[10]&&distance<','Pinching[h]=f.Valid[5]&&f.Valid[10]&&(old||f.CanStartPinch)&&distance<')
text=text.replace('colliders={ActiveColliders}"','colliders={ActiveColliders} observed={Source.Frames[0].ObservedCount},{Source.Frames[1].ObservedCount}"')
with (source/'BareHandInteraction.cs').open('x',encoding='utf8') as file:file.write(text)

text=(old/'Assets/MGFR/Scripts/BareHands/HandDepthMesh.cs').read_text(encoding='utf8')
text=text.replace('readonly Transform[] hierarchy;','readonly Transform[] hierarchy;\n  readonly float referenceWidth,referenceLength;\n  public bool FitSkin=true;public float SkinScale {get;private set;}=1;\n  double lastFit;')
text=text.replace('Renderer=Object.GetComponentInChildren<SkinnedMeshRenderer>();','referenceWidth=Vector3.Distance(Bones[7].position,Bones[22].position);\n   referenceLength=Vector3.Distance(Bones[1].position,Bones[12].position);\n   Renderer=Object.GetComponentInChildren<SkinnedMeshRenderer>();')
anchor='   // Parent-first order'
text=text.replace(anchor,'''   if(FitSkin)
   {
    float width=Vector3.Distance(f.Joints[7].position,f.Joints[22].position)/referenceWidth;
    float length=Vector3.Distance(f.Joints[1].position,f.Joints[12].position)/referenceLength;
    float target=Mathf.Clamp((width+length)*.5f,.85f,1.45f)*1.08f;
    double now=Time.realtimeSinceStartupAsDouble;float dt=lastFit==0?.016f:(float)(now-lastFit);lastFit=now;
    SkinScale=Mathf.Lerp(SkinScale,target,1-Mathf.Exp(-4*dt));Object.transform.localScale=Vector3.one*SkinScale;
   }
'''+anchor)
with (source/'HandDepthMesh.cs').open('x',encoding='utf8') as file:file.write(text)

text=(old/'Assets/MGFR/Editor/SkinnedHandsBuild.cs').read_text(encoding='utf8')
text=text.replace('mesh.Object.SetActive(true);','mesh.FitSkin=false;mesh.Object.SetActive(true);')
text=text.replace('mesh.Update(frame,false);','mesh.FitSkin=true;mesh.Update(frame,true);\n    for(int i=0;i<26;i++)if(Vector3.Distance(mesh.Bones[i].position,frame.Joints[i].position)>.00001f)throw new Exception("Skin fitting moved a joint");\n    mesh.Update(frame,false);')
with (source/'SkinnedHandsBuild.cs').open('x',encoding='utf8') as file:file.write(text)

replacements={p.name for p in source.iterdir()}
def ignore(path,names):return [n for n in names if n in replacements]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for path in source.iterdir():
    folder='Editor' if path.name.endswith('Build.cs') else 'Scripts/BareHands'
    target=project/'Assets/MGFR'/folder/path.name
    with path.open('rb') as reader,target.open('xb') as writer:shutil.copyfileobj(reader,writer)
print(project)
