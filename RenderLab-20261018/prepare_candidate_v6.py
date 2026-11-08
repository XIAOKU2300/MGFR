from pathlib import Path
import shutil
lab=Path('H:/MGFR/RenderLab-20261018');source=lab/'Sources/physics-v3';source.mkdir()
for original in (lab/'Sources/physics-v2').glob('*.cs'):
 text=original.read_text(encoding='utf8')
 if original.name=='PmxSecondaryPhysics.cs':
  text=text.replace('b.mode==0||b.mass>=1000||b.name.StartsWith','b.mode==0||b.name=="tail_jnt1"||b.name.StartsWith')
  text=text.replace('var d=Data.bodies[i];var go=Object(d.name);var rb=go.AddComponent<Rigidbody>();Bodies[i]=rb;',
   'var d=Data.bodies[i];var go=Object(d.name);go.transform.SetPositionAndRotation(V(d.position)*.08f,Rotation(d.rotation));var rb=go.AddComponent<Rigidbody>();Bodies[i]=rb;')
  text=text.replace('(Data.bodies[a].mask&(1<<Data.bodies[b].group))!=0||(Data.bodies[b].mask&(1<<Data.bodies[a].group))!=0',
   '(Data.bodies[a].mask&(1<<Data.bodies[b].group))==0||(Data.bodies[b].mask&(1<<Data.bodies[a].group))==0')
  text=text.replace('var a=Bodies[d.a];var b=Bodies[d.b];if(a.isKinematic&&b.isKinematic)continue;',
   'var a=Bodies[d.a];var b=Bodies[d.b];if(d.a==d.b||(a.isKinematic&&b.isKinematic))continue;')
  text=text.replace('j.anchor=b.transform.InverseTransformPoint(p);j.connectedAnchor=a.transform.InverseTransformPoint(p);',
   'j.anchor=Quaternion.Inverse(b.rotation)*(p-b.position);j.connectedAnchor=Quaternion.Inverse(a.rotation)*(p-a.position);')
  text=text.replace('j.axis=b.transform.InverseTransformDirection(frame*Vector3.right);j.secondaryAxis=b.transform.InverseTransformDirection(frame*Vector3.up);',
   'j.axis=Quaternion.Inverse(b.rotation)*(frame*Vector3.right);j.secondaryAxis=Quaternion.Inverse(b.rotation)*(frame*Vector3.up);')
  text=text.replace('j.rotationDriveMode=RotationDriveMode.XYAndZ;',
   'JointDrive LinearDrive(float spring)=>new JointDrive{positionSpring=spring*torqueScale/.0064f,positionDamper=Mathf.Sqrt(Mathf.Max(0,spring*torqueScale/.0064f))*.025f,maximumForce=100};\n    j.xDrive=LinearDrive(d.linearSpring[0]);j.yDrive=LinearDrive(d.linearSpring[1]);j.zDrive=LinearDrive(d.linearSpring[2]);\n    j.rotationDriveMode=RotationDriveMode.XYAndZ;')
 if original.name=='PmxPhysicsReview.cs':
  text=text.replace('float chestPeak=0,rearPeak=0,peakMs=0,maxGap=0;','float chestPeak=0,rearPeak=0,peakMs=0,totalMs=0,maxGap=0;')
  text=text.replace('peakMs=Mathf.Max(peakMs,physics.LastMilliseconds);','peakMs=Mathf.Max(peakMs,physics.LastMilliseconds);totalMs+=physics.LastMilliseconds;')
  text=text.replace('peakPhysicsCpuMs={peakMs}\\n','peakPhysicsCpuMs={peakMs}\\nmeanPhysicsCpuMs={totalMs/frames}\\n')
 with (source/original.name).open('x',encoding='utf8') as f:f.write(text)
project=lab/'Project-v6';project.mkdir()
for folder in ('Assets','Packages','ProjectSettings'):
 def ignore(path,names):return [n for n in names if Path(path).name=='PhysicsRig' and n.endswith('.cs')]
 shutil.copytree(lab/'Project-v5'/folder,project/folder,ignore=ignore)
for p in source.glob('*.cs'):
 with p.open('rb') as r,(project/'Assets/MGFR/Scripts/PhysicsRig'/p.name).open('xb') as w:shutil.copyfileobj(r,w)
print(project)
