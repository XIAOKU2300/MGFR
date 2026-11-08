from pathlib import Path
import shutil, hashlib, difflib, json

lab = Path(__file__).resolve().parent
root = Path('H:/MGFR/unity-client')
prior = Path('H:/MGFR/HandLab-20261018/Algorithm-v14/Candidate-1')
candidate = lab/'Candidate'
project = lab/'Project'
assert not candidate.exists() and not project.exists()
base = Path('Assets/MGFR/Scripts/BareHands')
changes = {p.relative_to(prior): p.read_text(encoding='utf-8-sig') for p in prior.rglob('*') if p.is_file()}

def replace_once(s, a, b):
    assert s.count(a) == 1, (a[:90], s.count(a))
    return s.replace(a, b)

s = (lab/'HandSurfaceQuery.cs').read_text(encoding='utf8')
s = s.replace('sealed class Compare:', 'sealed class CentroidComparer:').replace('new Compare{', 'new CentroidComparer{')
changes[base/'HandSurfaceQuery.cs'] = s

s = changes[base/'HandDepthMesh.cs']
s = s.replace('if(!active)return;', 'if(!active||AnatomicalOcclusion)return;')
s = s.replace('depthInset=1.5mm calibration=False', 'metricEnvelope=True automaticJointRadii=True globalEnlargement=False')
changes[base/'HandDepthMesh.cs'] = s

s = changes[base/'HandJointSource.cs']
s = s.replace('public bool CanStartPinch=>Observed[5]&&Observed[10];', 'public bool CanStartPinch=>Tracked&&Valid[5]&&Valid[10]&&Observed[5]&&Observed[10];')
s = s.replace('origin.TransformPoint(pose.position),origin.rotation*pose.rotation', 'origin!=null?origin.TransformPoint(pose.position):pose.position,origin!=null?origin.rotation*pose.rotation:pose.rotation')
s = s.replace('raw.Radius[i]=joint.TryGetRadius(out float r)?Mathf.Clamp(r,.004f,.025f):.008f;', 'raw.Radius[i]=joint.TryGetRadius(out float r)&&r>0&&float.IsFinite(r)?Mathf.Clamp(r,.004f,.025f):0;')
s = replace_once(s, '   AcceptSample(h,raw,type,Time.realtimeSinceStartupAsDouble);', '''   // Missing provider radii scale with observed palm width, never a global pose gain.
   float width=raw.Valid[7]&&raw.Valid[22]?Vector3.Distance(raw.Joints[7].position,raw.Joints[22].position):.065f;
   for(int i=0;i<26;i++)if(raw.Valid[i]&&raw.Radius[i]<=0)
    raw.Radius[i]=Mathf.Clamp(width*(i<2?.24f:i==5||i==10||i==15||i==20||i==25?.10f:.135f),.004f,.025f);
   AcceptSample(h,raw,type,Time.realtimeSinceStartupAsDouble);''')
s = replace_once(s, '    raw.Joints[i]=new Pose(', '''    if(!float.IsFinite(pose.position.sqrMagnitude)||!float.IsFinite(pose.rotation.x)||!float.IsFinite(pose.rotation.y)||!float.IsFinite(pose.rotation.z)||!float.IsFinite(pose.rotation.w))continue;
    raw.Joints[i]=new Pose(''')
changes[base/'HandJointSource.cs'] = s

s = changes[base/'BareHandInteraction.cs']
s = s.replace('readonly float[] acquireDelay=new float[2],breakTime=new float[2];', '''readonly float[] acquireDelay=new float[2],breakTime=new float[2];
  readonly Vector3[] previousAcquire=new Vector3[2];readonly bool[] hasAcquire=new bool[2];''')
s = s.replace('Release(h);pinchState[h].Reset();', 'Release(h);hasAcquire[h]=false;pinchState[h].Reset();')
s = s.replace('Release(h);blockedUntilOpen[h]=true;recoveryRemaining[h]=.10f;', 'Release(h);hasAcquire[h]=false;blockedUntilOpen[h]=true;recoveryRemaining[h]=.10f;')
s = replace_once(s, '     Release(h);\n     // A predicted', '     Release(h);hasAcquire[h]=false;\n     // A predicted')
s = replace_once(s, '    {TryGrab(h,target);acquireDelay[h]=1f/30f;}', '''    {TryGrab(h,target);previousAcquire[h]=f.PinchPoint;hasAcquire[h]=true;acquireDelay[h]=1f/30f;}''')
s = s.replace('Mathf.Clamp((f.Radius[a]+f.Radius[b])*.5f,.005f,.017f)', 'Mathf.Clamp((f.Radius[a]+f.Radius[b])*.5f,.004f,.025f)')
s = replace_once(s, '   if(!surfaceQuery.Find(Physics.Loader.transform.TransformPoint(target),reach,GrabbedBody[1-h],out int selected,out var point))return;', '''   var world=Physics.Loader.transform.TransformPoint(target);
   if(!surfaceQuery.FindSwept(hasAcquire[h]?previousAcquire[h]:world,world,reach,GrabbedBody[1-h],out int selected,out var point))return;''')
# PD velocity feed-forward lets contact proxies follow motion without raising stiffness.
s = replace_once(s, 'var force=rb.mass*(frequency*frequency*(target-rb.position)-2*frequency*rb.linearVelocity);', '''float modelScale=Mathf.Max(.0001f,Mathf.Abs(Physics.Loader.transform.lossyScale.x));
     var feed=Vector3.ClampMagnitude(velocity[h]/modelScale,2/modelScale);
     var force=rb.mass*(frequency*frequency*(target-rb.position)-2*frequency*(rb.linearVelocity-feed));''')
s = s.replace('F8 显示/隐藏手部轮廓 · F9 徒手/手柄', 'F8 手部包络 · F9 徒手/手柄 · 捏住后可移向布面')
changes[base/'BareHandInteraction.cs'] = s

s = changes[base/'HandOcclusionEnvelope.cs']
# Add a thenar capsule linking the thumb root to the palm; preserve finger gaps.
s = s.replace('const int Sides=10,Rings=8,SegmentVertices=Sides*Rings;', 'const int Sides=12,Rings=8,SegmentVertices=Sides*Rings,Segments=20;')
s = s.replace('19*SegmentVertices', 'Segments*SegmentVertices').replace('19*(Rings-1)', 'Segments*(Rings-1)').replace('s<19', 's<Segments')
s = replace_once(s, 'int a=HandDepthMesh.Segments[s,0],b=HandDepthMesh.Segments[s,1];', 'int a=s<19?HandDepthMesh.Segments[s,0]:1,b=s<19?HandDepthMesh.Segments[s,1]:2;')
s = replace_once(s, 'Vector3 p=f.Joints[a].position,q=f.Joints[b].position;', '''Vector3 p=f.Joints[a].position,q=f.Joints[b].position;
    if(s==19)p=Vector3.Lerp(f.Joints[1].position,f.Joints[0].position,.4f);''')
s = replace_once(s, 'float ra=Mathf.Max(.003f,radii[a]-.0007f),rb=Mathf.Max(.003f,radii[b]-.0007f);', '''float ra=Mathf.Max(.003f,radii[a]-.0007f),rb=Mathf.Max(.003f,radii[b]-.0007f);
    if(s==19)ra=rb=Mathf.Clamp(Vector3.Distance(f.Joints[7].position,f.Joints[22].position)*.18f,.008f,.022f);''')
s = s.replace('else if(f.Observed[i])radii[i]=Mathf.Lerp(radii[i],radius,alpha);', 'else if(f.Observed[i]&&radius>radii[i]*.65f&&radius<radii[i]*1.5f)radii[i]=Mathf.Lerp(radii[i],radius,alpha);')
s = s.replace('var normal=Vector3.Cross(across,along).normalized;', 'var normal=Vector3.Cross(across,along).normalized;\n   if(normal.sqrMagnitude<.5f)normal=f.Joints[1].rotation*Vector3.forward;')
changes[base/'HandOcclusionEnvelope.cs'] = s

manifest=[];patch=[]
for p, text in changes.items():
    dest=candidate/p;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf8',newline='\n') as f:f.write(text)
    source=root/p
    old=source.read_text(encoding='utf-8-sig') if source.exists() else ''
    if source.exists():
        backup=lab/'Originals'/p;backup.parent.mkdir(parents=True,exist_ok=True)
        with backup.open('xb') as f:f.write(source.read_bytes())
    manifest.append({'target':str(source),'exists':source.exists(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None,'candidate':str(dest)})
    patch.extend(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix()))
with (lab/'changes.patch').open('x',encoding='utf8') as f:f.writelines(patch)
with (lab/'manifest.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2,ensure_ascii=False)

# New isolated project: every destination is new. Existing source and packages stay intact.
def ignore(path,names):
    return [n for n in names if (Path(path)/n).relative_to(root) in changes]
def ignore_package(path,names):
    return [n for n in names if n in ('Tests','Tests.meta','DocCodeSamples.Tests','DocCodeSamples.Tests.meta','Samples~','Documentation~')]
shutil.copytree(root/'Assets',project/'Assets',ignore=ignore)
shutil.copytree(root/'ProjectSettings',project/'ProjectSettings')
shutil.copytree(root/'Packages',project/'Packages',ignore=ignore_package)
for package in (root/'Library/PackageCache').iterdir():
    if package.is_dir() and (package/'package.json').is_file():
        dest=project/'Packages'/package.name.split('@')[0]
        if not dest.exists():shutil.copytree(package,dest,ignore=ignore_package)
for p in changes:
    dest=project/p;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write((candidate/p).read_bytes())
review=(Path('H:/MGFR/HandLab-20261018/Algorithm-v14/AlgorithmReview.cs')).read_text(encoding='utf8')
review=review.replace('envelope.Mesh.vertexCount<2000', 'envelope.Mesh.vertexCount<2200')
with (project/'Assets/MGFR/Editor/AlgorithmReview.cs').open('x',encoding='utf8') as f:f.write(review)
print(json.dumps({'project':str(project),'existing_files_to_merge':sum(x['exists'] for x in manifest),'new_source_files':sum(not x['exists'] for x in manifest)},ensure_ascii=False))
