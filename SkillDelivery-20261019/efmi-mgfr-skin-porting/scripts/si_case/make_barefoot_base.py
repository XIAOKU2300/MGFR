"""Create a new barefoot, flat-foot rest mesh; never overwrite a skin."""
from pathlib import Path
import argparse,copy,hashlib,json,struct
import numpy as np
from scipy.optimize import brentq
from caseio import read_base,emit_json,normals

ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
assert not args.out.exists(),'Output must be a new directory'
m,a,morphs=read_base(args.input);report=json.loads((args.input/'conversion-report.json').read_text(encoding='utf-8'))
pos,norm,uv,bi,bw,idx,bind,sub=a
source_hashes={str(args.input/name):hashlib.sha256((args.input/name).read_bytes()).hexdigest() for name in ('si_model.json','si_model.bin')}
shoe=next(p for p in report['parts'] if p['part']=='shoes');body=next(p for p in report['parts'] if p['part']=='body')
body_ids=np.arange(body['vertexStart'],body['vertexStart']+body['vertices'])
original=pos.copy();absolute=np.array([b['positionScaled'] for b in m['bones']])
angles={};pivots={};foot_metrics={}
def turn(points,side,angle):
    t=np.deg2rad(angle);R=np.array([[1,0,0],[0,np.cos(t),-np.sin(t)],[0,np.sin(t),np.cos(t)]])
    return (points-pivots[side])@R.T+pivots[side]

for side,ankle in ((1,23),(-1,27)):
    pivots[side]=absolute[ankle].copy()
    sample=original[body_ids];sample=sample[(sample[:,0]*side>0)&(sample[:,1]<.15)]
    front=sample[sample[:,2]<-.065];heel=sample[sample[:,2]>.025]
    # Balance the actual plantar contact points, not the old high-heel toe bone.
    objective=lambda angle:float(turn(heel,side,angle)[:,1].min()-turn(front,side,angle)[:,1].min())
    angles[side]=float(brentq(objective,0,30))
    select=body_ids[(original[body_ids,0]*side>0)&(original[body_ids,1]<.155)]
    q=original[select];posed=turn(q,side,angles[side])
    # Keep calf above the ankle fixed; fade within the lower ankle/instep only.
    t=np.clip((q[:,1]-.09)/.065,0,1);strength=1-t*t*(3-2*t)
    pos[select]=q+(posed-q)*strength[:,None]
ground=float(pos[body_ids,1].min());pos[:,1]-=ground

# Remove only the explicit shoes draw group, including sole, heel and straps.
shoe_ids=np.arange(shoe['vertexStart'],shoe['vertexStart']+shoe['vertices'])
new_chunks=[];new_sub=[];offset=0
for start,count in sub:
    tri=idx[start:start+count].reshape(-1,3)
    reject=np.any((tri>=shoe_ids[0])&(tri<=shoe_ids[-1]),axis=1)
    result=tri[~reject].reshape(-1).copy();new_sub.append([offset,len(result)]);offset+=len(result);new_chunks.append(result)
removed_indices=len(idx)-offset;assert removed_indices==shoe['triangles']*3
idx=np.concatenate(new_chunks).astype('<u4')
used=np.unique(idx);remap=np.full(len(pos),-1,np.int64);remap[used]=np.arange(len(used))
idx=remap[idx].astype('<u4');pos,norm,uv,bi,bw=[arr[used] for arr in (pos,norm,uv,bi,bw)]
start,count=new_sub[7];body_tri=idx[start:start+count]
body_norm=normals(pos,body_tri);body_used=np.unique(body_tri);norm[body_used]=body_norm[body_used]

# Rest joints, IK targets and inverse binds follow the new neutral anatomy.
for side,joints in ((1,(7,8,23,24,744,745)),(-1,(10,11,27,28,740,741))):
    for joint in joints:absolute[joint]=turn(absolute[joint][None],side,angles[side])[0]
    for toe in ((8,24) if side==1 else (11,28)):
        absolute[toe,1]=ground+.018
absolute[:,1]-=ground
bind=np.tile(np.eye(4),(len(absolute),1,1));bind[:,:3,3]=-absolute
for k,bone in enumerate(m['bones']):
    bone['positionScaled']=absolute[k].tolist()
    bone['localScaled']=(absolute[k]-(absolute[bone['parent']] if bone['parent']>=0 else 0)).tolist()
new_morphs=[]
for shape,(ids,delta) in zip(m['blendShapes'],morphs):
    keep=remap[ids]>=0;new_ids=remap[ids[keep]].astype('<u4');shape['vertexCount']=len(new_ids);new_morphs.append((new_ids,delta[keep]))
for mat,(start,count) in zip(m['materials'],new_sub):mat.update(indexStart=start,faceIndexCount=count)
for side in (1,-1):
    old=original[body_ids];select=(old[:,0]*side>0)&(old[:,1]<.15);q=pos[remap[body_ids[select]]]
    orig=old[select];front=q[orig[:,2]<-.065];heel=q[orig[:,2]>.025]
    foot_metrics[str(side)]=dict(rotationDegrees=angles[side],forefootMinHeight=float(front[:,1].min()),heelMinHeight=float(heel[:,1].min()),
        soleMinHeight=float(q[:,1].min()),soleMaxContactGap=float(max(front[:,1].min(),heel[:,1].min())))
assert all(x['soleMaxContactGap']<.001 for x in foot_metrics.values())
assert pos[:,1].min()>-.00001
m['counts'].update(vertices=len(pos),indices=len(idx));m['boundsScaled']={'min':pos.min(0).tolist(),'max':pos.max(0).tolist()}
m['source']['modelName']='祀 蓝白泳装 · 赤脚平放';m['generatedBy']+=' + make_barefoot_base.py'
m['coordinateNote']+=' Barefoot: shoe draw group removed; foot plantar contact balanced, calf smoothly blended; mesh/rest joints lowered to ground, inverse binds rebuilt.'
new_parts=[]
for item in report['parts']:
    if item['part']=='shoes':continue
    item['vertexStart']=int(remap[item['vertexStart']]);new_parts.append(item)
report.update(version='barefoot-intermediate-not-visually-accepted',counts=m['counts'],triangles=len(idx)//3,bounds=m['boundsScaled'],parts=new_parts,
    barefoot=dict(shoeVerticesRemoved=len(shoe_ids),shoeTrianglesRemoved=removed_indices//3,bodyVerticalShiftMetres=-ground,feet=foot_metrics,
        method='Rotate foot around ankle to balance heel/forefoot contact; smooth calf transition; rebuild canonical rest and inverse bind matrices'),
    parentSkinHashes=source_hashes)
args.out.mkdir(parents=True,exist_ok=False);(args.out/'textures').mkdir()
for src in (args.input/'textures').iterdir():
    if src.is_file():
        with (args.out/'textures'/src.name).open('xb') as f:f.write(src.read_bytes())
with (args.out/'si_model.bin').open('xb') as f:
    f.write(struct.pack('<II',0x5346474d,1))
    for ar in (pos,norm,uv,bi,bw,idx,bind.astype('<f4'),np.array(new_sub,'<u4')):f.write(ar.tobytes())
    for ids,delta in new_morphs:f.write(ids.tobytes());f.write(delta.tobytes())
emit_json(args.out/'si_model.json',m);emit_json(args.out/'conversion-report.json',report)
for src,digest in source_hashes.items():assert hashlib.sha256(Path(src).read_bytes()).hexdigest()==digest
print(json.dumps({'counts':m['counts'],'barefoot':report['barefoot']},ensure_ascii=False))
