from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent
a=json.loads((R/'source-avatar.json').read_text(encoding='utf-8'))
h=a['m_Avatar']['m_Human']['data'];s=h['m_Skeleton']['data'];pose=h['m_SkeletonPose']['data']['m_X']
def vec(o,keys):return [o[k] for k in keys]
rest_t=np.array([vec(p['t'],'xyz') for p in pose]); rest_q=np.array([vec(p['q'],'xyzw') for p in pose])
nodes=h['m_HumanBoneIndex'][:22]
parents=[n['m_ParentId'] for n in s['m_Node']]
edges=[(0,1),(1,3),(3,5),(5,20),(0,2),(2,4),(4,6),(6,21),(0,7),(7,8),(8,9),(9,10),(10,11),(9,12),(12,14),(14,16),(16,18),(9,13),(13,15),(15,17),(17,19)]
image=Image.new('RGB',(1350,900),'#f5f4f0');draw=ImageDraw.Draw(image)
all_data=[]
for row,f in enumerate(sorted((R/'focused-probe-v2').glob('*.body.json'))):
 d=json.loads(f.read_text(encoding='utf-8')); frames=[]
 for sample in d['samples']:
  q=rest_q.copy();t=rest_t.copy()
  for b,value in zip(d['bones'],sample['rotations']):q[h['m_HumanBoneIndex'][b['Slot']]]=value
  t[nodes[0]]=sample['hips'];wp=[];wq=[]
  for i,parent in enumerate(parents):
   rr=Rotation.from_quat(q[i]); pp=t[i]
   if parent>=0: pp=wp[parent]+wq[parent].apply(pp);rr=wq[parent]*rr
   wp.append(pp);wq.append(rr)
  frames.append(np.array(wp)[nodes].tolist())
 all_data.append({'name':d['bones'][0]['Path'],'file':f.stem,'fps':d['fps'],'positions':frames,'edges':edges})
 for col,idx in enumerate([0,len(frames)//3,2*len(frames)//3]):
  p=np.array(frames[idx]); points=[]
  for x,y,z in p:points.append((col*450+225+(x+.40*z)*145,row*300+275-y*145))
  for e0,e1 in edges:draw.line([points[e0],points[e1]],fill='#234e63',width=5)
  for x,y in points:draw.ellipse((x-3,y-3,x+3,y+3),fill='#bd5e3c')
  draw.text((col*450+12,row*300+8),f.stem.replace('A_actor_jsspsi_','')[:44],fill='#222222')
  draw.text((col*450+12,row*300+25),f'frame {idx}',fill='#222222')
dest=R/'focused-body-poses-v1.png'
if dest.exists():raise FileExistsError(dest)
image.save(dest)
with (R/'focused-body-positions-v1.json').open('x',encoding='utf-8') as f:json.dump(all_data,f)
print(dest)
