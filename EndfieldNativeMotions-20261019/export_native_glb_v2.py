"""glTF 2.0 export of the original skin and selected native bone animations."""
from pathlib import Path
import json,struct,numpy as np,time
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'export-v2';OUT.mkdir(exist_ok=False)
model=json.loads((ROOT/'assets-v1/native-model.json').read_text(encoding='utf-8'));materials=json.loads((ROOT/'assets-v1/preview-materials.json').read_text(encoding='utf-8'))['materials'];manifest=json.loads((ROOT/'motions-v5/manifest.json').read_text(encoding='utf-8'))
binary=bytearray();views=[];accessors=[]
def view(raw):
 binary.extend(b'\0'*((-len(binary))%4));offset=len(binary);binary.extend(raw);views.append({'buffer':0,'byteOffset':offset,'byteLength':len(raw)});return len(views)-1
def accessor(values,kind,component=5126,bounds=False):
 dtype={5126:'<f4',5123:'<u2',5125:'<u4'}[component];v=np.asarray(values,dtype=dtype);row={'bufferView':view(v.tobytes()),'componentType':component,'count':len(v),'type':kind}
 if bounds:row.update(min=np.min(v,axis=0).reshape(-1).astype(float).tolist(),max=np.max(v,axis=0).reshape(-1).astype(float).tolist())
 accessors.append(row);return len(accessors)-1
def conv(values,kind):
 v=np.array(values,dtype='<f4',copy=True)
 if kind=='translation':v[...,2]*=-1
 elif kind=='rotation':v[...,:2]*=-1
 return v
nodes=[]
for i,n in enumerate(model['nodes']):
 node={'name':n['name'],'translation':conv(n['t'],'translation').tolist(),'rotation':conv(n['q'],'rotation').tolist(),'scale':n['s'],'extras':{'sourcePath':n['path']}}
 children=[j for j,b in enumerate(model['nodes']) if b['parent']==i]
 if children:node['children']=children
 nodes.append(node)
textures=[];images=[];texture_lookup={};gmaterials=[];mat_lookup={}
for m in materials:
 if m['texture'] not in texture_lookup:
  texture_lookup[m['texture']]=len(textures);images.append({'bufferView':view((ROOT/'assets-v1'/m['texture']).read_bytes()),'mimeType':'image/png'});textures.append({'source':len(images)-1,'sampler':0})
 gmaterials.append({'name':m['name'],'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':{'index':texture_lookup[m['texture']]},'metallicFactor':0,'roughnessFactor':.8},'doubleSided':True,'alphaMode':'MASK' if m['cutoff'] else 'OPAQUE','alphaCutoff':m['cutoff'],'extensions':{'KHR_materials_unlit':{}}});mat_lookup[m['name']]=len(gmaterials)-1
meshes=[];skins=[];mesh_roots=[];flip=np.diag([1,1,-1,1]);vertex_total=0
for m in model['meshes']:
 if any(token in m['name'] for token in ['shadow','cloth_05','cloth_06','cloth_07','cloth_08','cloth_09']):continue
 raw=(ROOT/'assets-v1'/m['file']).read_bytes();cursor=0;count=m['vertices']
 def take(shape,dtype):
  global cursor
  size=int(np.prod(shape))*np.dtype(dtype).itemsize;v=np.frombuffer(raw,dtype=dtype,count=int(np.prod(shape)),offset=cursor).reshape(shape).copy();cursor+=size;return v
 pos=take((count,3),'<f4');normal=take((count,3),'<f4');uv=take((count,2),'<f4');joints=take((count,4),'<u2');weights=take((count,4),'<f4');indices=take((m['indexCount'],),'<u4');bind=take((m['boneCount'],4,4),'<f4');assert cursor==len(raw)
 pos[:,2]*=-1;normal[:,2]*=-1;uv[:,1]=1-uv[:,1];weights/=weights.sum(axis=1,keepdims=True)
 attributes={'POSITION':accessor(pos,'VEC3',bounds=True),'NORMAL':accessor(normal,'VEC3'),'TEXCOORD_0':accessor(uv,'VEC2'),'JOINTS_0':accessor(joints,'VEC4',5123),'WEIGHTS_0':accessor(weights,'VEC4')}
 material=mat_lookup['M'+m['name'][1:].removesuffix('_lod0')];primitives=[]
 for s in m['submeshes']:
  tri=indices[s['first']:s['first']+s['count']].reshape(-1,3)[:,[0,2,1]].reshape(-1);primitives.append({'attributes':attributes,'indices':accessor(tri,'SCALAR',5125),'material':material,'mode':4})
 meshes.append({'name':m['name'],'primitives':primitives});ibm=(flip@bind@flip).transpose(0,2,1).reshape(m['boneCount'],16)
 skins.append({'name':m['name']+' skin','joints':m['bones'],'inverseBindMatrices':accessor(ibm,'MAT4'),'skeleton':0})
 mesh_roots.append(len(nodes));nodes.append({'name':m['name'],'mesh':len(meshes)-1,'skin':len(skins)-1});vertex_total+=count
animations=[];reports=[]
for clip in manifest['clips']:
 raw=(ROOT/'motions-v5'/clip['file']).read_bytes();magic,count,frames,fps=struct.unpack_from('<8sIIf',raw);assert magic==b'ENFMOT1\0' and count==len(model['nodes'])
 values=np.frombuffer(raw,dtype='<f4',offset=20).reshape(frames,count,10);times=np.arange(frames,dtype='<f4')/fps;alltime=None;endtime=None;channels=[];samplers=[];constants=0
 for index,n in enumerate(model['nodes']):
  for kind,section,rest in [('rotation',slice(0,4),n['q']),('translation',slice(4,7),n['t']),('scale',slice(7,10),n['s'])]:
   data=values[:,index,section]
   if np.max(np.abs(data-np.array(rest)))<1e-7:continue
   constant=bool(np.max(np.abs(data-data[0]))<1e-7)
   if constant:
    if endtime is None:endtime=accessor(times[[0,-1]],'SCALAR',bounds=True)
    time_index=endtime;v=data[[0,-1]];constants+=1
   else:
    if alltime is None:alltime=accessor(times,'SCALAR',bounds=True)
    time_index=alltime;v=data
   v=conv(v,kind);output=accessor(v,'VEC4' if kind=='rotation' else 'VEC3');channels.append({'sampler':len(samplers),'target':{'node':index,'path':kind}});samplers.append({'input':time_index,'output':output,'interpolation':'LINEAR'})
 animations.append({'name':clip['label'],'channels':channels,'samplers':samplers,'extras':{'sourceName':clip['name'],'loopSuggested':clip.get('loop',False),'authoredFacialComposition':clip.get('authored_composition',False)}})
 reports.append({'name':clip['name'],'frames':frames,'channels':len(channels),'constant_channels_reduced_to_endpoints':constants});print(clip['name'],len(channels),'channels',flush=True)
document={'asset':{'version':'2.0','generator':'Original Endfield Si native assets + ACL/Humanoid offline conversion'},'extensionsUsed':['KHR_materials_unlit'],'scene':0,'scenes':[{'name':'Original Endfield Si','nodes':[0]+mesh_roots}],'nodes':nodes,'meshes':meshes,'skins':skins,'materials':gmaterials,'textures':textures,'images':images,'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}],'animations':animations,'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors,'extras':{'scope':'Original native character model and rig. No MGFR model or rig.','limitations':['Native custom foot/toe controls included; neutral-rig axes checked, original-engine frame comparison not performed.','Generic idle/walk have 12 unrelated source transform paths excluded; only matching source rig paths are exported.','Simplified unlit albedo materials; no original shader, cloth simulation or original-game frame equality claim.','Facial transitions, backing idle and unilateral wink are authored preview compositions using original character facial data.']}}
assert all(v['byteOffset']+v['byteLength']<=len(binary) for v in views)
assert all(max(s['joints'])<len(model['nodes']) for s in skins)
js=json.dumps(document,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*((-len(js))%4);binary.extend(b'\0'*((-len(binary))%4));dest=OUT/'Si-native-selected.glb'
with dest.open('xb') as f:f.write(struct.pack('<III',0x46546c67,2,12+8+len(js)+8+len(binary)));f.write(struct.pack('<II',len(js),0x4e4f534a));f.write(js);f.write(struct.pack('<II',len(binary),0x004e4942));f.write(binary)
with (OUT/'export-report.json').open('x',encoding='utf-8') as f:json.dump({'glb':str(dest),'bytes':dest.stat().st_size,'vertices':vertex_total,'meshes':len(meshes),'skin_bones':len(model['nodes']),'animations':reports},f,indent=2)
print(dest,dest.stat().st_size)
