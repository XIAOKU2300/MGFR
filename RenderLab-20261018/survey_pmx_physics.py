"""Read the previously skipped PMX physics tail without changing its reader."""
from pathlib import Path
import sys,json,collections
root=Path('H:/MGFR');sys.path.insert(0,str(root/'tools/pmx'))
import pmx_reader as pmx
class TailReader(pmx._Reader):
 instance=None
 def __init__(self,data):
  super().__init__(data);TailReader.instance=self
pmx._Reader=TailReader
path=next(root.glob('【明日方舟*祀*'))/'祀.pmx'
model=pmx.read_pmx(str(path));r=TailReader.instance
text=lambda:pmx._read_text(r,model.encoding)
for _ in range(r.int32()):
 text();text();r.uint8()
 for _ in range(r.int32()):
  kind=r.uint8();r.index(model.index_sizes['bone' if kind==0 else 'morph'],signed=True)
bodies=[]
for i in range(r.int32()):
 name=text();english=text();bone=r.index(model.index_sizes['bone'],signed=True)
 group=r.uint8();mask=r.uint16();shape=r.uint8();size=r.floats(3);position=r.floats(3);rotation=r.floats(3)
 mass,linear,angular,restitution,friction=r.floats(5);mode=r.uint8()
 bodies.append(dict(index=i,name=name,bone=bone,boneName=model.bones[bone].name if bone>=0 else '',group=group,mask=mask,shape=shape,size=size,position=position,rotation=rotation,mass=mass,linearDamping=linear,angularDamping=angular,restitution=restitution,friction=friction,mode=mode))
joints=[]
for i in range(r.int32()):
 name=text();text();kind=r.uint8();a=r.index(model.index_sizes['rigidbody'],signed=True);b=r.index(model.index_sizes['rigidbody'],signed=True)
 joints.append(dict(name=name,kind=kind,a=a,b=b,position=r.floats(3),rotation=r.floats(3),linearLower=r.floats(3),linearUpper=r.floats(3),angularLower=r.floats(3),angularUpper=r.floats(3),linearSpring=r.floats(3),angularSpring=r.floats(3)))
report=dict(bodies=bodies,joints=joints)
out=root/'RenderLab-20261018/pmx-physics-survey.json'
with out.open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
hits=collections.Counter()
for ids,weights in zip(model.bone_indices,model.bone_weights):
 for i,w in zip(ids,weights):
  if w>.00001:hits[i]+=1
print('Bodies',len(bodies),'joints',len(joints),'modes',dict(collections.Counter(b['mode'] for b in bodies)))
for b in bodies:
 if not (b['name'].startswith('裙子_') or any(x in b['name'] for x in ['发','髪'])):
  print(b['index'],b['name'],'bone',b['bone'],b['boneName'],'mode',b['mode'],'group',b['group'],'weighted',hits[b['bone']])
