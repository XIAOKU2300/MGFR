"""Native Endfield mesh/material/texture decoding, using installed read-only inputs.
Writes only a new assets directory. No game process or game DLL is loaded.
"""
from pathlib import Path
import sys,json,struct,io,hashlib,collections
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
WORK=Path('H:/MGFR/work/si-animation-20261019')
sys.path.insert(0,str(WORK))
from extract_verified import read_payload
from bundle_reader import Helper,read_bundle
from typetree_reader import tree_objects,read_object

def new_bytes(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(data)
def new_json(p,data):new_bytes(p,json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8'))

def main():
 out=ROOT/'assets-v1';out.mkdir(exist_ok=False)
 resources=WORK/'resource-map'
 assets=json.loads((resources/'si-verified-assets.json').read_text(encoding='utf-8'))
 bundles={b['name']:b for b in json.loads((resources/'si-resolved-bundles.json').read_text(encoding='utf-8'))}
 selected=[a for a in assets if '/actor/girl/jsspsi/' in a['path'].lower() and Path(a['path']).suffix.lower() in ['.mat','.tga','.png','.dds']]
 targets={a['bundle'] for a in selected}
 materials=[];textures=[];receipts=[];helper=Helper('OfflineDecoder.dll')
 try:
  for bundle in sorted(targets):
   packed=read_payload(bundles[bundle]['row'])
   receipts.append({'bundle':bundle,'sha256':hashlib.sha256(packed).hexdigest(),'vfs_md5_verified':True})
   nodes=read_bundle(packed,helper);streams=dict(nodes)
   for cab,data in nodes:
    if '.resS' in cab or '.resource' in cab:continue
    for obj in tree_objects(data):
     if obj['class_id'] not in [21,28]:continue
     value=read_object(obj);name=value['m_Name']
     if obj['class_id']==21:
      materials.append({'name':name,'pathId':obj['path_id'],'cab':cab,'properties':value})
     else:
      payload=value['image data'];stream=value['m_StreamData']
      if not payload and stream['size']:
       source=streams[stream['path'].split('/')[-1]]
       payload=source[stream['offset']:stream['offset']+stream['size']]
       assert len(payload)==stream['size']
      width=value['m_Width'];height=value['m_Height'];fmt=value['m_TextureFormat']
      if fmt in [10,12,24,25,26,27]:
       dxgi={10:71,12:77,24:95,25:98,26:80,27:83}[fmt]
       pitch=((width+3)//4)*((height+3)//4)*(8 if fmt in [10,26] else 16)
       header=[124,0x81007,height,width,pitch,0,1]+[0]*11+[32,4,struct.unpack('<I',b'DX10')[0],0,0,0,0,0]+[0x1000,0,0,0,0]
       assert len(header)==31
       dds=b'DDS '+struct.pack('<31I',*header)+struct.pack('<5I',dxgi,3,0,1,0)+payload[:pitch]
       image=Image.open(io.BytesIO(dds));image.load()
      elif fmt in [3,4]:image=Image.frombytes('RGB' if fmt==3 else 'RGBA',(width,height),payload[:width*height*(3 if fmt==3 else 4)])
      else:raise ValueError(f'Unsupported texture format {fmt} for {name}')
      image=image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
      dest=out/'textures'/(name+'.png');dest.parent.mkdir(exist_ok=True)
      with dest.open('xb') as f:image.save(f,format='PNG')
      textures.append({'name':name,'pathId':obj['path_id'],'cab':cab,'file':str(dest.relative_to(out)).replace('\\','/'),'width':width,'height':height,'textureFormat':fmt})
   print('decoded',bundle,flush=True)
  nodes=read_bundle(Path('H:/MGFR/SiMotions-20261019/bundles/9e412ddfc434a71dcf834d6e.ab').read_bytes(),helper)
 finally:helper.close()
 avatar=json.loads(Path('H:/MGFR/MotionConversionResearch-20261019/source-avatar.json').read_text(encoding='utf-8'))
 skeleton=avatar['m_Avatar']['m_AvatarSkeleton']['data'];pose=avatar['m_Avatar']['m_AvatarSkeletonPose']['data']['m_X'];tos={p['first']:p['second'] for p in avatar['m_TOS']}
 lookup={h:i for i,h in enumerate(skeleton['m_ID'])}
 model={'name':avatar['m_Name'],'nodes':[{'name':tos[h].split('/')[-1] or 'AvatarRoot','path':tos[h],'parent':skeleton['m_Node'][i]['m_ParentId'],'t':[pose[i]['t'][c] for c in 'xyz'],'q':[pose[i]['q'][c] for c in 'xyzw'],'s':[pose[i]['s'][c] for c in 'xyz']} for i,h in enumerate(skeleton['m_ID'])],'meshes':[],'materials':materials,'textures':textures,'notes':['Original mesh and original Avatar; no MGFR/PMX inputs.','Packed normals are regenerated from native triangle topology for this preview.','Mesh coordinate rotation: (x,y,z) -> (x,z,-y). Original inverse bind matrices retained with matching coordinate conversion.']}
 coordinate=np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]],dtype=np.float64)
 sizes={0:4,1:2,2:1,3:1,4:2,5:2,6:1,7:1,8:2,9:2,10:4,11:4}
 dtypes={0:'<f4',1:'<f2',2:'u1',3:'i1',4:'<u2',5:'<i2',6:'u1',7:'i1',8:'<u2',9:'<i2',10:'<u4',11:'<i4'}
 for cab,data in nodes:
  for obj in tree_objects(data):
   if obj['class_id']!=43:continue
   m=read_object(obj);name=m['m_Name']
   if not name.endswith('_lod0') or '_vfxpart_' in name or '_shadow_' in name:continue
   v=m['m_VertexData'];count=v['m_VertexCount'];channels=v['m_Channels'];raw=v['m_DataSize'];strides={}
   for ch in channels:
    dim=ch['dimension']&15
    if dim:strides[ch['stream']]=max(strides.get(ch['stream'],0),ch['offset']+sizes[ch['format']]*dim)
   offsets={};cursor=0
   for stream,stride in sorted(strides.items()):offsets[stream]=cursor;cursor=(cursor+count*stride+15)&~15
   assert cursor-15<=len(raw)<=cursor,(name,len(raw),cursor)
   def channel(index):
    c=channels[index];dim=c['dimension']&15
    if not dim:return None
    dt=np.dtype(dtypes[c['format']]);data=np.ndarray((count,dim),dtype=dt,buffer=raw,offset=offsets[c['stream']]+c['offset'],strides=(strides[c['stream']],dt.itemsize)).copy()
    if c['format'] in [2,4]:data=data.astype(np.float32)/(255 if c['format']==2 else 65535)
    elif c['format'] in [3,5]:data=np.maximum(data.astype(np.float32)/(127 if c['format']==3 else 32767),-1)
    return data
   positions=channel(0).astype('<f4')@coordinate[:3,:3].T
   uv=channel(4).astype('<f4');joints=channel(13).astype('<u2');weights=channel(12)
   if weights is None:weights=np.tile(np.array([1,0,0,0],dtype='<f4'),(count,1))
   weights=weights.astype('<f4');weights/=np.maximum(weights.sum(axis=1,keepdims=True),1e-12)
   assert int(joints.max())<len(m['m_BoneNameHashes'])
   indices=np.frombuffer(m['m_IndexBuffer'],dtype='<u4' if m['m_IndexFormat']==1 else '<u2').astype('<u4')
   # Submesh triangles are made explicit to account for baseVertex.
   submeshes=[];allindices=[]
   for sub in m['m_SubMeshes']:
    assert sub['topology']==0
    first=sub['firstByte']//(4 if m['m_IndexFormat']==1 else 2);arr=indices[first:first+sub['indexCount']]+sub['baseVertex']
    submeshes.append({'first':sum(len(v) for v in allindices),'count':len(arr)});allindices.append(arr)
   indices=np.concatenate(allindices);assert indices.max()<count
   normals=np.zeros_like(positions);tri=indices.reshape(-1,3);face=np.cross(positions[tri[:,1]]-positions[tri[:,0]],positions[tri[:,2]]-positions[tri[:,0]])
   for k in range(3):np.add.at(normals,tri[:,k],face)
   normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
   bind=np.array([[[p[f'e{r}{c}'] for c in range(4)] for r in range(4)] for p in m['m_BindPose']])@np.linalg.inv(coordinate)
   bones=[lookup[h] for h in m['m_BoneNameHashes']]
   dest=out/'meshes'/(name+'.bin');blocks=[positions.astype('<f4'),normals.astype('<f4'),uv,joints,weights,indices,bind.astype('<f4')]
   new_bytes(dest,b''.join(v.tobytes() for v in blocks))
   model['meshes'].append({'name':name,'file':str(dest.relative_to(out)).replace('\\','/'),'vertices':count,'indexCount':len(indices),'boneCount':len(bones),'bones':bones,'submeshes':submeshes,'bytes':dest.stat().st_size})
 new_json(out/'native-model.json',model);new_json(out/'source-receipts.json',receipts)
 print('native assets:',len(model['nodes']),'nodes',len(model['meshes']),'meshes',sum(m['vertices'] for m in model['meshes']),'verts',len(textures),'textures',len(materials),'materials')
if __name__=='__main__':main()
