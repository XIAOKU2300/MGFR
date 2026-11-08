"""Finalize atlas routing without changing the first conversion or any source assets."""
from pathlib import Path
import argparse,copy,json,struct
import numpy as np
from build_swimsuit_v1 import read_base,emit_json

p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
m,a,morphs=read_base(args.input);report=json.loads((args.input/'conversion-report.json').read_text(encoding='utf-8'))
pos,norm,uv,bi,bw,idx,bind,sub=a
parts=report['parts'];offset=len(pos)-sum(x['vertices'] for x in parts)
for part in parts:
    part['vertexStart']=offset
    if part['part'] in ('horn','tail_base','tail_detail'):
        # These sample existing PMX PNGs: matched original vertices prove that
        # raw game V already equals the converted PMX V. Newly decoded DDS differs.
        uv[offset:offset+part['vertices'],1]=1-uv[offset:offset+part['vertices'],1]
    offset+=part['vertices']
material_indices=[idx[start:start+count].copy() for start,count in sub]
# Component 3 tail pieces share its NEW swimsuit atlas, not original Cloth1 PNG.
tail_count=sum(x['triangles']*3 for x in parts if x['part'] in ('tail','tail_accessory'))
assert tail_count==8124
material_indices[8]=np.concatenate([material_indices[8],material_indices[14][:tail_count]])
material_indices[14]=material_indices[14][tail_count:]
for part in parts:
    if part['part'] in ('tail','tail_accessory'):part['material']=8
sub=[];offset=0
for i,mat in enumerate(m['materials']):
    count=len(material_indices[i]);mat.update(indexStart=offset,faceIndexCount=count);sub.append([offset,count]);offset+=count
idx=np.concatenate(material_indices).astype('<u4');m['generatedBy']='tools/skins/build_swimsuit_v1.py + finalize_swimsuit_v2.py'
args.out.mkdir(parents=True,exist_ok=False);(args.out/'textures').mkdir()
for f in (args.input/'textures').iterdir():
    if f.is_file():
        with (args.out/'textures'/f.name).open('xb') as out:out.write(f.read_bytes())
with (args.out/'si_model.bin').open('xb') as f:
    f.write(struct.pack('<II',0x5346474d,1))
    for arr in (pos,norm,uv,bi,bw,idx,bind,np.array(sub,'<u4')):f.write(arr.tobytes())
    for ids,delta in morphs:f.write(ids.tobytes());f.write(delta.tobytes())
m['coordinateNote']='EFMI -> MGFR positions (-x,z,y); new DDS atlas UV V flipped, retained PMX atlas UV V unchanged. Arms raised 13.115 degrees; canonical parent-relative rest and inverse binds.'
emit_json(args.out/'si_model.json',m)
report.update(version=2,atlasCorrections=['component 3 tail pieces use swimsuit atlas','horn/original tail components use unflipped game V with existing PMX PNGs'])
emit_json(args.out/'conversion-report.json',report)
print(args.out)
