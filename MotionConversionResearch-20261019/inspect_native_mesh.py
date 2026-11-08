"""Read only the already-extracted native model bundle; record mesh contracts."""
from pathlib import Path
import sys,json,numpy as np,collections,zlib
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parent
OUT=Path('H:/MGFR/EndfieldNativeMotions-20261019')
OUT.mkdir(exist_ok=False)
sys.path.insert(0,'H:/MGFR/work/si-animation-20261019')
from bundle_reader import Helper,read_bundle
from typetree_reader import tree_objects,read_object
avatar=json.loads((ROOT/'source-avatar.json').read_text(encoding='utf-8'))
s=avatar['m_Avatar']['m_AvatarSkeleton']['data'];pose=avatar['m_Avatar']['m_AvatarSkeletonPose']['data']['m_X']
tos={p['first']:p['second'] for p in avatar['m_TOS']};lookup={h:i for i,h in enumerate(s['m_ID'])}
for h in s['m_ID']:lookup.setdefault(zlib.crc32(tos[h].split('/')[-1].encode()),lookup[h])
world=[]
for i,node in enumerate(s['m_Node']):
 p=pose[i];m=np.eye(4);m[:3,:3]=Rotation.from_quat([p['q'][c] for c in 'xyzw']).as_matrix()@np.diag([p['s'][c] for c in 'xyz']);m[:3,3]=[p['t'][c] for c in 'xyz']
 if node['m_ParentId']>=0:m=world[node['m_ParentId']]@m
 world.append(m)
h=Helper('OfflineDecoder.dll')
try:nodes=read_bundle(Path('H:/MGFR/SiMotions-20261019/bundles/9e412ddfc434a71dcf834d6e.ab').read_bytes(),h)
finally:h.close()
report=[]
for node,data in nodes:
 for o in tree_objects(data):
  if o['class_id']!=43:continue
  m=read_object(o);v=m['m_VertexData'];hashes=m['m_BoneNameHashes'];missing=[x for x in hashes if x not in lookup]
  transforms=[]
  for bh,bind in zip(hashes,m['m_BindPose']):
   if bh not in lookup:continue
   b=np.array([[bind[f'e{r}{c}'] for c in range(4)] for r in range(4)])
   transforms.append(world[lookup[bh]]@b)
  matrices=np.array(transforms)
  row={'name':m['m_Name'],'path_id':o['path_id'],'vertices':v['m_VertexCount'],'bones':len(hashes),'missing_bones':missing,'channels':v['m_Channels'],'vertex_bytes':len(v['m_DataSize']),'submeshes':m['m_SubMeshes'],'index_format':m['m_IndexFormat'],'indices_bytes':len(m['m_IndexBuffer']),'mesh_compression':m['m_MeshCompression'],'bind_consistency_max':float(np.abs(matrices-matrices[0]).max()) if len(matrices) else None,'mesh_to_avatar':matrices[0].tolist() if len(matrices) else None}
  report.append(row)
with (OUT/'mesh-contracts.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print('meshes',len(report))
for r in report:
 if 'lod0' in r['name'].lower():print(r['name'],r['vertices'],'bones',r['bones'],'missing',len(r['missing_bones']),'binderr',round(r['bind_consistency_max'],6))
print('first M',report[0]['mesh_to_avatar'])
