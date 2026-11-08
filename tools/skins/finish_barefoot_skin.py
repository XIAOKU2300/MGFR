"""Package barefoot skin, smoothing coincident skin normals across UV seams."""
from pathlib import Path
import argparse,json,struct,hashlib
import numpy as np
from build_swimsuit_v1 import read_base,emit_json

ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
m,a,morphs=read_base(args.input);pos,norm,uv,bi,bw,idx,bind,sub=a
start,count=sub[7];tri=idx[start:start+count].reshape(-1,3);body=np.unique(tri)
_,group=np.unique(np.round(pos[body]*1e5).astype(np.int64),axis=0,return_inverse=True)
lookup=np.full(len(pos),-1,np.int64);lookup[body]=group
cross=np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]])
sums=np.zeros((group.max()+1,3),float)
for k in range(3):np.add.at(sums,lookup[tri[:,k]],cross)
length=np.linalg.norm(sums,axis=1);good=length>1e-12;sums[good]/=length[good,None];sums[~good]=[0,1,0]
norm[body]=sums[group]
args.out.mkdir(parents=True,exist_ok=False);(args.out/'textures').mkdir()
for src in (args.input/'textures').iterdir():
    if src.is_file():
        with (args.out/'textures'/src.name).open('xb') as f:f.write(src.read_bytes())
with (args.out/'si_model.bin').open('xb') as f:
    f.write(struct.pack('<II',0x5346474d,1))
    for ar in (pos,norm,uv,bi,bw,idx,bind,sub):f.write(ar.tobytes())
    for ids,delta in morphs:f.write(ids.tobytes());f.write(delta.tobytes())
m['generatedBy']+=' + finish_barefoot_skin.py';emit_json(args.out/'si_model.json',m)
r=json.loads((args.input/'conversion-report.json').read_text(encoding='utf-8'));r['barefoot']['skinNormals']='Area-weighted, shared at coincident body vertices without welding UV or geometry'
emit_json(args.out/'conversion-report.json',r)
base=Path(r'H:\MGFR\converted\skins\si-swimsuit-ready');old,_,_=read_base(base)
checks=dict(boneNamesOrderAndParentsIdentical=[(b['name'],b['parent']) for b in m['bones']]==[(b['name'],b['parent']) for b in old['bones']],
            morphNamesAndOrderIdentical=[s['name'] for s in m['blendShapes']]==[s['name'] for s in old['blendShapes']],
            materialsUnchanged=[s['name'] for s in m['materials']]==[s['name'] for s in old['materials']],
            parentSkinUnchanged=all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in r['parentSkinHashes'].items()),
            sourceFilesUnchanged=all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in r['sourceHashes'].items()),
            finiteData=all(np.isfinite(x).all() for x in (pos,norm,uv,bw,bind)),
            validIndices=bool(idx.max()<len(pos) and bi.max()<828),
            weightsNormalized=bool(np.max(np.abs(bw.sum(1)-1))<1e-5),
            normalsNormalized=bool(np.max(np.abs(np.linalg.norm(norm,axis=1)-1))<1e-5),
            soleContactUnderOneMillimetre=all(v['soleMaxContactGap']<.001 for v in r['barefoot']['feet'].values()),
            noGeometryBelowGround=bool(pos[:,1].min()>-.00001),
            shoePartAbsent=all(p['part']!='shoes' for p in r['parts']))
absolute=np.array([b['positionScaled'] for b in m['bones']]);checks['inverseBindMatchesRest']=bool(np.max(np.abs(bind[:,:3,3]+absolute))<1e-6)
checks['canonicalRestCoordinates']=all(np.max(np.abs(np.array(b['localScaled'])-(absolute[i]-(absolute[b['parent']] if b['parent']>=0 else 0))))<1e-6 for i,b in enumerate(m['bones']))
assert all(checks.values()),checks
checks['allPassed']=True;emit_json(args.out/'contract-checks.json',checks)
emit_json(args.out/'skin.json',dict(id='si-swimsuit-barefoot',name='祀 · 蓝白泳装 · 赤脚平放',version=1,format='MGFR model binary v1',
    entry={'json':'si_model.json','binary':'si_model.bin','textures':'textures'},counts=m['counts'],feet=r['barefoot'],
    materialBindings=[dict(slots=[7],albedo='textures/swimsuit_body_D.png',normalData='textures/swimsuit_body_N.png'),
                      dict(slots=[8,10],albedo='textures/swimsuit_cloth_D.png',normalData='textures/swimsuit_cloth_N.png',sourceLightData='textures/swimsuit_cloth_L.png')],
    standingHeightMetres=float(pos[:,1].max()),restPoseChanged=True,existingCharacterReplaced=False))
print(json.dumps(checks))
