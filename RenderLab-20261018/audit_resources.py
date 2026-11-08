from pathlib import Path
from PIL import Image,ImageDraw
import json,numpy as np,struct
root=Path('H:/MGFR');lab=root/'RenderLab-20261018';source=next(root.glob('【明日方舟*祀*'))/'other tex'
names=['T_actor_jsspsi_face_01_D.png','T_actor_common_female_face_01_SDF.png','T_actor_jsspsi_face_01_ST.png','T_actor_jsspsi_face_01_N.png','T_actor_jsspsi_cloth_01_D.png','T_actor_jsspsi_cloth_01_P.png','T_actor_jsspsi_hair_01_D.png','T_actor_jsspsi_hair_01_HN.png','T_actor_jsspsi_hair_01_ST.png','T_actor_jsspsi_hair_01_P.png']
canvas=Image.new('RGB',(1280,len(names)*250),(40,40,40));draw=ImageDraw.Draw(canvas)
for row,name in enumerate(names):
 im=Image.open(source/name).convert('RGBA');im.thumbnail((240,220));canvas.paste(im.convert('RGB'),(0,row*250+25));draw.text((5,row*250+5),name,fill='white')
 raw=Image.open(source/name).convert('RGBA')
 for c,ch in enumerate(raw.split()):
  ch.thumbnail((240,220));canvas.paste(ch,(256*(c+1),row*250+25));draw.text((256*(c+1)+5,row*250+5),'RGBA'[c],fill='white')
canvas.save(lab/'channel-audit.png')
d=json.loads((root/'unity-client/Assets/StreamingAssets/si/si_model.json').read_text(encoding='utf8'))
binary=(root/'unity-client/Assets/StreamingAssets/si/si_model.bin').read_bytes();n=d['counts']['vertices']
positions=np.frombuffer(binary,'<f4',n*3,8).reshape(-1,3)
uv=np.frombuffer(binary,'<f4',n*2,8+n*24).reshape(-1,2)
indices=np.frombuffer(binary,'<u4',d['counts']['indices'],8+n*56)
face=np.unique(indices[:8196]);sdf=np.asarray(Image.open(source/names[1]).convert('RGBA'))
samples=[]
for x,y in [(0,1.5),(-.025,1.51),(.025,1.51),(-.04,1.48),(.04,1.48),(0,1.45),(0,1.54)]:
 candidates=face[positions[face,2]<-.025]
 i=candidates[np.argmin((positions[candidates,0]-x)**2+(positions[candidates,1]-y)**2)]
 u,v=uv[i]; color=sdf[min(1023,int((1-v)*1024)),min(1023,int(u*1024))].tolist()
 samples.append(dict(position=positions[i].tolist(),uv=uv[i].tolist(),sdf=color))
with (lab/'face-uv-audit.json').open('x',encoding='utf8') as f:json.dump(samples,f,indent=2)
print(json.dumps(samples))
