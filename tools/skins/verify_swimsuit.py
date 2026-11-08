"""Verify the independently packaged model against the original data contract."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
from build_swimsuit_v1 import read_base,emit_json

p=argparse.ArgumentParser();p.add_argument('skin',type=Path);args=p.parse_args()
base=Path(r'H:\MGFR\converted\si');old,oa,om=read_base(base);m,a,morphs=read_base(args.skin)
report=json.loads((args.skin/'conversion-report.json').read_text(encoding='utf-8'))
checks={}
checks['boneNamesOrderAndParentsIdentical']=[(b['name'],b['parent']) for b in m['bones']]==[(b['name'],b['parent']) for b in old['bones']]
checks['morphNamesAndOrderIdentical']=[s['name'] for s in m['blendShapes']]==[s['name'] for s in old['blendShapes']]
checks['materialNamesAndOrderIdentical']=[s['name'] for s in m['materials']]==[s['name'] for s in old['materials']]
checks['allSourceHashesUnchanged']=all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==digest for f,digest in report['sourceHashes'].items())
pos,norm,uv,bi,bw,idx,bind,sub=a
checks['finiteData']=all(np.isfinite(x).all() for x in (pos,norm,uv,bw,bind))
checks['validMeshIndices']=bool(idx.min()>=0 and idx.max()<len(pos) and len(idx)%3==0)
checks['validBoneIndices']=bool(bi.max()<828)
checks['normalLengthsValid']=bool(np.max(np.abs(np.linalg.norm(norm,axis=1)-1))<1e-5)
checks['weightsNormalized']=bool(np.max(np.abs(bw.sum(1)-1))<1e-5 and bw.min()>=0)
checks['allMaterialTexturesExist']=all(not mat.get('textureFile') or (args.skin/'textures'/mat['textureFile']).is_file() for mat in m['materials'])
checks['submeshRangesCoverAllIndices']=bool(sum(int(x[1]) for x in sub)==len(idx) and all(int(sub[i,0]+sub[i,1])==int(sub[i+1,0]) for i in range(len(sub)-1)))
checks['morphIndicesValid']=all(len(ids)==shape['vertexCount'] and (len(ids)==0 or int(ids.max())<len(pos)) for shape,(ids,delta) in zip(m['blendShapes'],morphs))
rest=np.array([x['positionScaled'] for x in m['bones']]);locals=np.array([x['localScaled'] for x in m['bones']])
checks['canonicalRestCoordinates']=all(np.max(np.abs(locals[i]-(rest[i]-(rest[b['parent']] if b['parent']>=0 else 0))))<1e-6 for i,b in enumerate(m['bones']))
checks['inverseBindMatchesRest']=bool(np.max(np.abs(bind[:,:3,3]+rest))<1e-6)
checks['allPassed']=all(checks.values())
emit_json(args.skin/'contract-checks.json',checks)
assert checks['allPassed'],checks
signature=hashlib.sha256(json.dumps([(x['name'],x['parent']) for x in m['bones']],ensure_ascii=False).encode()).hexdigest()
manifest=dict(id='si-swimsuit',name='祀 · 蓝白泳装',version=1,format='MGFR model binary v1',entry={'json':'si_model.json','binary':'si_model.bin','textures':'textures'},
              counts=m['counts'],skeletonSignature=signature,existingCharacterReplaced=False,clothSimulation='basic body-bound skinning',
              materialBindings=[dict(slots=[7],albedo='textures/swimsuit_body_D.png',normalData='textures/swimsuit_body_N.png'),
                                dict(slots=[8,10],albedo='textures/swimsuit_cloth_D.png',normalData='textures/swimsuit_cloth_N.png',sourceLightData='textures/swimsuit_cloth_L.png')],
              resourceHashes={str(f.relative_to(args.skin)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in args.skin.rglob('*') if f.is_file() and f.suffix in ('.bin','.png','.json')},
              worklog=r'H:\MGFR\docs\swimsuit-worklog-20261019.md')
emit_json(args.skin/'skin.json',manifest)
print(json.dumps(checks,ensure_ascii=False))
