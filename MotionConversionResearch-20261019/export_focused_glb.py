"""Export selected source-rig animation probes as glTF 2.0 GLB.
Skeleton only; no game mesh. Body solver v1 limitations remain explicit.
"""
from pathlib import Path
import json,struct,time
import numpy as np
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'source-rig-glb-v1';OUT.mkdir(exist_ok=False)
avatar=json.loads((ROOT/'source-avatar.json').read_text(encoding='utf-8'))
constant=avatar['m_Avatar'];skeleton=constant['m_AvatarSkeleton']['data']
pose=constant['m_AvatarSkeletonPose']['data']['m_X']
tos={p['first']:p['second'] for p in avatar['m_TOS']}
paths=[tos[k] for k in skeleton['m_ID']];lookup={p:i for i,p in enumerate(paths)}
hash_lookup={k:i for i,k in enumerate(skeleton['m_ID'])}
def vector(o,keys):return [o[k] for k in keys]
def convert(values,kind):
 v=np.array(values,dtype='<f4',copy=True)
 if kind=='translation':v[...,2]*=-1
 elif kind=='rotation':
  v[...,:2]*=-1;v/=np.linalg.norm(v,axis=-1,keepdims=True)
  for i in range(1,len(v)):
   if np.dot(v[i-1],v[i])<0:v[i]*=-1
 return v
reports=[]
for report in json.loads((ROOT/'focused-probe-v2/report.json').read_text(encoding='utf-8')):
 start=time.perf_counter();clip=json.loads(Path(report['clip']).read_text(encoding='utf-8'))
 body=json.loads(Path(report['body_result']).read_text(encoding='utf-8'))
 frames=body['frames'];fps=body['fps']; binary=bytearray();views=[];accessors=[]
 def accessor(values,typ):
  v=np.asarray(values,dtype='<f4');offset=len(binary);binary.extend(v.tobytes())
  view=len(views);views.append({'buffer':0,'byteOffset':offset,'byteLength':v.nbytes})
  row={'bufferView':view,'componentType':5126,'count':len(v),'type':typ}
  if typ=='SCALAR':row.update(min=[float(v.min())],max=[float(v.max())])
  accessors.append(row);return len(accessors)-1
 nodes=[]
 for i,p in enumerate(pose):
  q=convert([vector(p['q'],'xyzw')],'rotation')[0].tolist()
  node={'name':paths[i].split('/')[-1] or 'AvatarRoot','translation':convert([vector(p['t'],'xyz')],'translation')[0].tolist(),'rotation':q,'scale':vector(p['s'],'xyz'),'extras':{'sourcePath':paths[i]}}
  children=[j for j,n in enumerate(skeleton['m_Node']) if n['m_ParentId']==i]
  if children:node['children']=children
  nodes.append(node)
 tracks={};bindings=clip['m_ClipBindingConstant']['genericBindings']
 pos=[b for b in bindings if b['typeID']==4 and b['attribute']==1]
 rot=[b for b in bindings if b['typeID']==4 and b['attribute']==2]
 assert [b['path'] for b in pos]==[b['path'] for b in rot]
 ts=Path(report['scalar_samples']).with_name(Path(report['scalar_samples']).name.replace('.FloatBufferData.', '.TransformBufferData.'))
 raw=ts.read_bytes();header=struct.unpack_from('<8sBHIIff',raw)
 assert header[0]==b'ACLBAKE1' and header[1]==12 and header[3]==len(pos) and header[4]==frames
 data=np.frombuffer(raw,dtype='<f4',offset=27).reshape(frames,len(pos),10)
 face_tracks=0;face_changing=0
 for j,b in enumerate(pos):
  index=hash_lookup[b['path']]
  tracks[index,'translation']=data[:,j,4:7];tracks[index,'rotation']=data[:,j,:4]
  if '/face_Head/' in paths[index]:
   face_tracks+=1
   if np.max(np.ptp(data[:,j,:7],axis=0))>1e-5:face_changing+=1
 for j,b in enumerate(body['bones']):tracks[lookup[b['Path']],'rotation']=np.array([f['rotations'][j] for f in body['samples']])
 hips=lookup[next(b['Path'] for b in body['bones'] if b['Slot']==0)]
 tracks[hips,'translation']=np.array([f['hips'] for f in body['samples']])
 times=accessor(np.arange(frames,dtype='<f4')/fps,'SCALAR');samplers=[];channels=[]
 for (index,kind),values in sorted(tracks.items()):
  if not np.isfinite(values).all():raise ValueError('nonfinite')
  v=convert(values,kind);out=accessor(v,'VEC4' if kind=='rotation' else 'VEC3')
  channels.append({'sampler':len(samplers),'target':{'node':index,'path':kind}})
  samplers.append({'input':times,'output':out,'interpolation':'LINEAR'})
 meta={'asset':{'version':'2.0','generator':'MGFR isolated source-rig feasibility probe v1'},'scene':0,'scenes':[{'nodes':[i for i,n in enumerate(skeleton['m_Node']) if n['m_ParentId']<0]}],'nodes':nodes,'animations':[{'name':report['name'],'samplers':samplers,'channels':channels}],'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors,'extras':{'status':'research probe; skeleton only; not MGFR-ready','knownLimitations':['Six custom foot/toe DOFs omitted','No original-game frame comparison','Root scale/IK equivalence not validated','No mesh/target-model retargeting'],'sourceAvatar':avatar['m_Name']}}
 js=json.dumps(meta,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*((-len(js))%4);binary.extend(b'\0'*((-len(binary))%4))
 dest=OUT/(report['name']+'.glb')
 with dest.open('xb') as f:
  f.write(struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(binary)));f.write(struct.pack('<II',len(js),0x4e4f534a));f.write(js);f.write(struct.pack('<II',len(binary),0x004e4942));f.write(binary)
 # Validate binary bounds and every channel's input/output lengths.
 assert all(v['byteOffset']+v['byteLength']<=len(binary) for v in views)
 assert all(accessors[x['output']]['count']==frames for x in samplers)
 reports.append({'name':report['name'],'file':str(dest),'nodes':len(nodes),'channels':len(channels),'frames':frames,'face_bones':face_tracks,'animated_face_bones':face_changing,'bytes':dest.stat().st_size,'seconds':time.perf_counter()-start})
 print(report['name'],reports[-1])
with (OUT/'validation.json').open('x',encoding='utf-8') as f:json.dump(reports,f,indent=2)
