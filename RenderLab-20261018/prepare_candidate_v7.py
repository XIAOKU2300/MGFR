from pathlib import Path
import shutil
lab=Path('H:/MGFR/RenderLab-20261018');source=lab/'Sources/physics-v4';source.mkdir()
original=lab/'Sources/physics-v3/PmxPhysicsReview.cs';text=original.read_text(encoding='utf8')
text=text.replace('totalMs=0,maxGap=0;','totalMs=0,maxGap=0,maxViolation=0;string worst="";')
old='float gap=Vector3.Distance(j.transform.TransformPoint(j.anchor),j.connectedBody.transform.TransformPoint(j.connectedAnchor));maxGap=Mathf.Max(maxGap,gap);'
new='''Vector3 delta=j.transform.TransformPoint(j.anchor)-j.connectedBody.transform.TransformPoint(j.connectedAnchor);
     maxGap=Mathf.Max(maxGap,delta.magnitude);
     Vector3 x=j.transform.TransformDirection(j.axis).normalized,y=j.transform.TransformDirection(j.secondaryAxis).normalized,z=Vector3.Cross(x,y).normalized;
     float Error(ConfigurableJointMotion motion,float amount)=>motion==ConfigurableJointMotion.Free?0:Mathf.Max(0,Mathf.Abs(amount)-(motion==ConfigurableJointMotion.Locked?0:j.linearLimit.limit));
     float violation=Mathf.Max(Error(j.xMotion,Vector3.Dot(delta,x)),Mathf.Max(Error(j.yMotion,Vector3.Dot(delta,y)),Error(j.zMotion,Vector3.Dot(delta,z))));
     if(violation>maxViolation){maxViolation=violation;worst=j.gameObject.name;}
'''
assert old in text;text=text.replace(old,new)
text=text.replace('maxGap<.2f','maxViolation<.035f')
text=text.replace('maxJointAnchorGapMetres={maxGap}\\n','maxJointAnchorGapMetres={maxGap}\\nmaxTranslationConstraintViolationMetres={maxViolation}\\nworstConstraintBody={worst}\\n')
with (source/original.name).open('x',encoding='utf8') as f:f.write(text)
project=lab/'Project-v7';project.mkdir()
for folder in ('Assets','Packages','ProjectSettings'):
 def ignore(path,names):return ['PmxPhysicsReview.cs'] if Path(path).name=='PhysicsRig' and 'PmxPhysicsReview.cs' in names else []
 shutil.copytree(lab/'Project-v6'/folder,project/folder,ignore=ignore)
with (source/original.name).open('rb') as r,(project/'Assets/MGFR/Scripts/PhysicsRig'/original.name).open('xb') as w:shutil.copyfileobj(r,w)
print(project)
