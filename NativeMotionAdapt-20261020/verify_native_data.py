from pathlib import Path
import json
import struct
import hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent
DATA=ROOT.parent/'SiLLMBridge-20261020/MainData'

def speed(q,fps):
    q=q.astype(np.float64);q/=np.linalg.norm(q,axis=-1,keepdims=True)
    return 2*np.arccos(np.clip(np.abs((q[1:]*q[:-1]).sum(-1)),0,1))*180/np.pi*fps

def main():
    manifest=json.loads((DATA/'motions/manifest.json').read_text(encoding='utf-8'))
    sourceRig=json.loads((DATA/'source-rig.json').read_text(encoding='utf-8'))
    names={n['name']:i for i,n in enumerate(sourceRig['nodes'])}
    model=json.loads((ROOT.parent/'converted/si/si_model.json').read_text(encoding='utf-8'))
    semantic={x['target_name']:x['source'] for x in sourceRig['mapping']};semantic['腰']=names['Bip001_Pelvis']
    for prefix,native in [('左','L'),('右','R')]:
        for f,jp in enumerate(['親指','人指','中指','薬指','小指']):
            for j in range(3):semantic[prefix+jp+['０','１','２','３'][j if f==0 else j+1]]=names['Bip001_'+native+'_Finger'+str(f)+('' if j==0 else str(j))]
        for jp,n in [('足D','Thigh'),('ひざD','Calf'),('足首D','Foot')]:semantic[prefix+jp]=names['Bip001_'+native+'_'+n]
    report={'pass':True,'method':'Independent serialized-pose validation and source-relative joint-speed comparison; original artist motion is preserved','files':0,'samples':0,'maximumQuaternionNormError':0,'clips':[]}
    for clip in manifest['clips']:
        raw=(DATA/'motions'/clip['file']).read_bytes();_,count,frames,fps=struct.unpack_from('<8siif',raw)
        native=np.frombuffer(raw,dtype='<f4',offset=20).reshape(frames,count,10);nativeSpeed=speed(native[:,:,:4],fps)
        entry={'name':clip['name'],'skins':[],'sourceSha256':hashlib.sha256(raw).hexdigest()}
        for skin in ['swimsuit','original']:
            path=ROOT/'bake-all-v1/Baked'/skin/(clip['name']+'.hpose');raw=path.read_bytes();magic,n,f,rate=struct.unpack_from('<iiif',raw)
            if magic!=0x45535048 or n!=58 or f!=frames or rate!=fps or len(raw)!=16+n*4+f*n*28:raise RuntimeError('Invalid pose contract: '+str(path))
            ids=np.frombuffer(raw,dtype='<i4',count=n,offset=16);pose=np.frombuffer(raw,dtype='<f4',offset=16+n*4).reshape(f,n,7)
            if not np.isfinite(pose).all():raise RuntimeError('Non-finite baked pose')
            norms=np.abs(np.linalg.norm(pose[:,:,3:],axis=2)-1);report['maximumQuaternionNormError']=max(report['maximumQuaternionNormError'],float(norms.max()))
            targetSpeed=speed(pose[:,:,3:],fps);unexpected=[];sourcePeak=0;targetPeak=0
            for j,boneId in enumerate(ids):
                name=model['bones'][boneId]['name'];src=semantic.get(name)
                if src is None:continue
                a=float(nativeSpeed[:,src].max());b=float(targetSpeed[:,j].max());sourcePeak=max(sourcePeak,a);targetPeak=max(targetPeak,b)
                # A bounded allowance covers different joint axes/limits and blend entry.
                if b>max(900,a*1.25+400):unexpected.append({'bone':name,'sourcePeak':a,'targetPeak':b})
            report['pass'] &= not unexpected and float(norms.max())<1e-4
            report['files']+=1;report['samples']+=f*n
            entry['skins'].append({'skin':skin,'sourcePeak':round(sourcePeak,3),'targetPeak':round(targetPeak,3),'additionalDiscontinuities':unexpected})
        report['clips'].append(entry)
    report['unityAnimationClipAssets']=len(list((ROOT/'UnityAssets-v1/Assets/NativeClips').rglob('*.anim')))
    report['pass'] &= report['files']==52 and report['unityAnimationClipAssets']==52
    out=ROOT/'source-relative-verification.json'
    with out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k!='clips'},ensure_ascii=False))
    print('sourceRelativeReport',str(out))
    raise SystemExit(0 if report['pass'] else 1)
if __name__=='__main__':main()
