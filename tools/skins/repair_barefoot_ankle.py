"""Restore the calf, limiting the flat-foot correction to below the ankle."""
from pathlib import Path
import argparse,hashlib,json,struct
import numpy as np
from build_swimsuit_v1 import read_base,emit_json

ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--fade-start',type=float,default=.09);ap.add_argument('--fade-end',type=float,default=.155);args=ap.parse_args()
assert not args.out.exists()
source=Path(r'H:\MGFR\converted\skins\si-swimsuit-ready')
sm,sa,_=read_base(source);m,a,morphs=read_base(args.input)
r=json.loads((args.input/'conversion-report.json').read_text(encoding='utf-8'))
sr=json.loads((source/'conversion-report.json').read_text(encoding='utf-8'))
pos,norm,uv,bi,bw,idx,bind,sub=a
sb=next(x for x in sr['parts'] if x['part']=='body');body=next(x for x in r['parts'] if x['part']=='body')
original=sa[0][sb['vertexStart']:sb['vertexStart']+sb['vertices']].astype(float)
q=original.copy();shift=r['barefoot']['bodyVerticalShiftMetres']
for side,ankle in ((1,23),(-1,27)):
    pivot=np.array(sm['bones'][ankle]['positionScaled']);theta=np.deg2rad(r['barefoot']['feet'][str(side)]['rotationDegrees'])
    rot=np.array([[1,0,0],[0,np.cos(theta),-np.sin(theta)],[0,np.sin(theta),np.cos(theta)]])
    mask=original[:,0]*side>0;v=original[mask]
    t=np.clip((v[:,1]-args.fade_start)/(args.fade_end-args.fade_start),0,1);strength=1-t*t*(3-2*t)
    q[mask]=v+(((v-pivot)@rot.T+pivot)-v)*strength[:,None]
q[:,1]+=shift
start=body['vertexStart'];pos[start:start+body['vertices']]=q
calf=original[:,1]>=args.fade_end
expected=original[calf].copy();expected[:,1]+=shift
calf_error=float(np.max(np.abs(q[calf]-expected)))
assert calf_error<1e-7 and pos[:,1].min()>-.00001
# Smooth normals across duplicate skin vertices without welding texture coordinates.
offset,count=sub[7];tri=idx[offset:offset+count].reshape(-1,3);vertices=np.unique(tri)
_,group=np.unique(np.round(pos[vertices]*1e5).astype(np.int64),axis=0,return_inverse=True)
lookup=np.full(len(pos),-1,np.int64);lookup[vertices]=group
area=np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]])
sums=np.zeros((group.max()+1,3),float)
for k in range(3):np.add.at(sums,lookup[tri[:,k]],area)
length=np.linalg.norm(sums,axis=1);valid=length>1e-12;sums[valid]/=length[valid,None];sums[~valid]=[0,1,0]
norm[vertices]=sums[group]
args.out.mkdir(parents=True,exist_ok=False);(args.out/'textures').mkdir()
for src in (args.input/'textures').iterdir():
    if src.is_file():
        with (args.out/'textures'/src.name).open('xb') as f:f.write(src.read_bytes())
with (args.out/'si_model.bin').open('xb') as f:
    f.write(struct.pack('<II',0x5346474d,1))
    for ar in (pos,norm,uv,bi,bw,idx,bind,sub):f.write(ar.tobytes())
    for ids,delta in morphs:f.write(ids.tobytes());f.write(delta.tobytes())
m['generatedBy']+=' + repair_barefoot_ankle.py';m['source']['modelName']='祀 蓝白泳装 · 赤脚脚踝修正'
m['coordinateNote']+=' Ankle repair: calf vertices above the ankle are restored exactly; foot correction fades only below the ankle.'
emit_json(args.out/'si_model.json',m)
r['barefoot']['ankleRepair']=dict(cause='Previous 0.16..0.28m fade rotated lower-calf vertices and created a visible S bend',
    fadeStartMetres=args.fade_start,fadeEndMetres=args.fade_end,maxCalfShapeChangeMetres=calf_error,
    originalCalfRestored=True,previousVisualAcceptanceRejected=True)
emit_json(args.out/'conversion-report.json',r)
print(json.dumps(r['barefoot']['ankleRepair']))
