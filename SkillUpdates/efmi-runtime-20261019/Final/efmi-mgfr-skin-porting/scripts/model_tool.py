"""Read-only MGFR inspection and model-contract validation."""
from pathlib import Path
import argparse,hashlib,json,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).parent/'si_case'))
from caseio import read_base,emit_json

def signature(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def verify(root,base=None):
    m,a,shapes=read_base(Path(root));p,n,u,bi,bw,ix,bind,sub=a
    absolute=np.array([b['positionScaled'] for b in m['bones']])
    parents=[b['parent'] for b in m['bones']]
    checks=dict(finiteArrays=all(np.isfinite(x).all() for x in (p,n,u,bw,bind)),
        indexRange=bool(len(ix)%3==0 and (not len(ix) or ix.max()<len(p))),
        boneIndexRange=bool(bi.max()<len(m['bones'])),weightsNormalized=bool(bw.min()>=0 and np.max(np.abs(bw.sum(1)-1))<1e-5),
        normalLengths=bool(np.max(np.abs(np.linalg.norm(n,axis=1)-1))<1e-5),
        parentsValid=all(-1<=b<len(parents) and b!=i for i,b in enumerate(parents)),
        submeshesCoverIndices=bool(sum(int(v[1]) for v in sub)==len(ix) and all(int(sub[i,0]+sub[i,1])==int(sub[i+1,0]) for i in range(len(sub)-1))),
        materialRangesMatchJson=all([mat['indexStart'],mat['faceIndexCount']]==list(map(int,sub[i])) for i,mat in enumerate(m['materials'])),
        materialTexturesExist=all(not x.get('textureFile') or (Path(root)/'textures'/x['textureFile']).is_file() for x in m['materials']),
        morphIndicesValid=all(len(ids)==s['vertexCount'] and (not len(ids) or ids.max()<len(p)) and np.isfinite(delta).all() for s,(ids,delta) in zip(m['blendShapes'],shapes)),
        inverseBindsMatchRest=bool(np.max(np.abs(bind[:,:3,3]+absolute))<1e-6),
        parentRelativeRest=all(np.max(np.abs(np.array(b['localScaled'])-(absolute[i]-(absolute[b['parent']] if b['parent']>=0 else 0))))<1e-6 for i,b in enumerate(m['bones'])))
    # Validate cycles separately: a parent can legally appear after its child.
    cycle=False
    for i in range(len(parents)):
        seen=set();j=i
        while j>=0:
            if j in seen:cycle=True;break
            seen.add(j)
            if j>=len(parents):cycle=True;break
            j=parents[j]
    checks['noBoneCycles']=not cycle
    if base:
        bm,_,_=read_base(Path(base))
        checks['rigNamesOrderParentsPreserved']=[(b['name'],b['parent']) for b in m['bones']]==[(b['name'],b['parent']) for b in bm['bones']]
        checks['morphNamesOrderPreserved']=[b['name'] for b in m['blendShapes']]==[b['name'] for b in bm['blendShapes']]
        checks['materialSlotsPreserved']=[b['name'] for b in m['materials']]==[b['name'] for b in bm['materials']]
    return dict(allPassed=all(checks.values()),checks=checks,counts=m['counts'],triangles=len(ix)//3,
        maxWeightSumError=float(np.max(np.abs(bw.sum(1)-1))),minY=float(p[:,1].min()),
        visualStatus='Numerical checks only; render and user visual review are separate')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['inspect','verify']);ap.add_argument('model',type=Path);ap.add_argument('--base',type=Path);ap.add_argument('--report',type=Path);args=ap.parse_args()
    if args.command=='inspect':
        m,_,_=read_base(args.model);result=dict(counts=m['counts'],bounds=m['boundsScaled'],rigSignature=signature([(b['name'],b['parent']) for b in m['bones']]),morphSignature=signature([s['name'] for s in m['blendShapes']]))
    else:result=verify(args.model,args.base)
    if args.report:emit_json(args.report,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result.get('allPassed',True) else 1

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,IndexError,AssertionError) as exc:
        print('Model check failed: '+str(exc),file=sys.stderr);sys.exit(2)
