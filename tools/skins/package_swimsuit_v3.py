"""Produce the clean 14-material skin; omit the old game's tail machinery."""
from pathlib import Path
import argparse,json,struct
import numpy as np
from build_swimsuit_v1 import read_base,emit_json

p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
m,a,morphs=read_base(args.input);report=json.loads((args.input/'conversion-report.json').read_text(encoding='utf-8'))
pos,norm,uv,bi,bw,idx,bind,sub=a
# Slot 14 contains only old tail-base/detail ornaments with a different atlas.
# Keep the swimsuit's main tail and matching blue-white accessory in slot 8.
cut=int(sub[14,0]);idx=idx[:cut].copy();used=np.unique(idx);remap=np.full(len(pos),-1,np.int64);remap[used]=np.arange(len(used))
idx=remap[idx].astype('<u4');pos,norm,uv,bi,bw=[x[used] for x in (pos,norm,uv,bi,bw)]
new_morphs=[]
for shape,(ids,delta) in zip(m['blendShapes'],morphs):
    valid=remap[ids]>=0;ids=remap[ids[valid]].astype('<u4');delta=delta[valid];shape['vertexCount']=len(ids);new_morphs.append((ids,delta))
m['materials']=m['materials'][:14];m['counts'].update(vertices=len(pos),indices=len(idx),materials=14)
m['boundsScaled']={'min':pos.min(0).tolist(),'max':pos.max(0).tolist()};m['generatedBy']+=' + package_swimsuit_v3.py'
report['parts']=[x for x in report['parts'] if x['part'] not in ('tail_base','tail_detail')]
for item in report['parts']:item['vertexStart']=int(remap[item['vertexStart']])
report.update(version=3,counts=m['counts'],triangles=len(idx)//3,bounds=m['boundsScaled'],omittedParts=['original game mechanical tail-base/detail ornaments'],
              materialSlotContract='14 slots, same semantic order as the current character')
args.out.mkdir(parents=True,exist_ok=False);(args.out/'textures').mkdir()
for f in (args.input/'textures').iterdir():
    if f.is_file():
        with (args.out/'textures'/f.name).open('xb') as out:out.write(f.read_bytes())
with (args.out/'si_model.bin').open('xb') as f:
    f.write(struct.pack('<II',0x5346474d,1))
    for ar in (pos,norm,uv,bi,bw,idx,bind,sub[:14]):f.write(ar.tobytes())
    for ids,delta in new_morphs:f.write(ids.tobytes());f.write(delta.tobytes())
emit_json(args.out/'si_model.json',m);emit_json(args.out/'conversion-report.json',report)
assert np.max(np.abs(bw.sum(1)-1))<1e-5 and idx.max()<len(pos)
print(json.dumps(m['counts']))
