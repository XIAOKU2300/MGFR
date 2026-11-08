from pathlib import Path
import importlib.util
import hashlib
import json
import struct
import numpy as np

HERE=Path(__file__).resolve().parent
FINAL=HERE.parents[1]
ROOT=Path('H:/MGFR')
DATA=ROOT/'SiLLMBridge-20261020/MainData'
ACTIVE=FINAL/'Player/MGFR_Data/StreamingAssets/native-actions'
spec=importlib.util.spec_from_file_location('binding',HERE.parent/'bind_native_reference.py')
binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
rig=json.loads((DATA/'source-rig.json').read_text(encoding='utf-8'))['nodes']
source_names={b['name']:i for i,b in enumerate(rig)}
source_ids=[source_names[n] for n in ['Bip001_L_Foot','Bip001_L_Toe0','Bip001_R_Foot','Bip001_R_Toe0']]
restq=np.array([[b['q'] for b in rig]])
restp=np.array([[b['t'] for b in rig]])
sq,_=binding.fk(rig,restq,restp,source_ids)
c=np.array([0.,1.,0.,0.])
restworld={i:binding.mul(c,sq[i][0]) for i in source_ids}
manifest=json.loads((DATA/'motions/manifest.json').read_text(encoding='utf-8'))['clips']
report={'scope':'Only remove ankle-to-toe direction fitting introduced by the prior update. Official source files unchanged. No manual angle, IK, pose clamp, filtering or resampling.',
        'allClipsNativeFootDelta':True,'allOtherChannelsByteIdentical':True,'clips':[],'targets':[]}
for skin,relative in [('swimsuit','skins/si-swimsuit-barefoot-ankle-v4/si_model.json'),('original','si/si_model.json')]:
    bones=json.loads((FINAL/'Player/MGFR_Data/StreamingAssets'/relative).read_text(encoding='utf-8'))['bones']
    if skin=='original' and bones[17]['positionScaled'][1]>=3:
        absolute=np.array([b['localScaled'] for b in bones])
        for i,b in enumerate(bones):b['localScaled']=(absolute[i]-(absolute[b['parent']] if b['parent']>=0 else 0)).tolist()
    names={b['name']:i for i,b in enumerate(bones)}
    target_ids=[names[n] for n in ['左足首','左つま先','右足首','右つま先']]
    allowed=set(target_ids)|{740,744}
    for clip in manifest:
        active=ACTIVE/skin/(clip['name']+'.hpose')
        candidate=HERE/'native-source-feet'/skin/active.name
        old=active.read_bytes();new=candidate.read_bytes()
        magic,count,frames,fps=struct.unpack_from('<iiif',new)
        assert magic==0x45535048 and new[:16+count*4]==old[:16+count*4]
        ids=np.frombuffer(new,dtype='<i4',offset=16,count=count)
        a=np.frombuffer(old,dtype='<f4',offset=16+count*4).reshape(frames,count,7)
        b=np.frombuffer(new,dtype='<f4',offset=16+count*4).reshape(frames,count,7)
        changed=[int(ids[i]) for i in range(count) if a[:,i].tobytes()!=b[:,i].tobytes()]
        assert set(changed)<=allowed and a[:,:,:3].tobytes()==b[:,:,:3].tobytes()
        nativepath=DATA/'motions'/clip['file'];raw=nativepath.read_bytes()
        assert raw[:8]==b'ENFMOT1\0'
        n,nf,rate=struct.unpack_from('<iif',raw,8);assert (n,nf,rate)==(len(rig),frames,fps)
        values=np.frombuffer(raw,dtype='<f4',offset=20).reshape(frames,n,10)
        source_world,_=binding.fk(rig,values[:,:,:4],values[:,:,4:7],source_ids)
        tq=np.tile([0.,0.,0.,1.],(frames,len(bones),1));tq[:,ids]=b[:,:,3:]
        tp=np.broadcast_to(np.array([[v['localScaled'] for v in bones]]),(frames,len(bones),3)).copy();tp[:,ids]=b[:,:,:3]
        target_world,_=binding.fk(bones,tq,tp,target_ids)
        errors=[]
        for si,ti in zip(source_ids,target_ids):
            expected=binding.mul(binding.mul(c,source_world[si]),binding.inv(restworld[si]))
            actual=target_world[ti]
            dot=np.abs(np.sum(expected*actual,axis=-1)/(np.linalg.norm(expected,axis=-1)*np.linalg.norm(actual,axis=-1)))
            errors.append(float(np.max(np.degrees(2*np.arccos(np.clip(dot,0,1))))))
        assert max(errors)<.0002 and np.isfinite(b).all()
        report['clips'].append({'skin':skin,'name':clip['name'],'frames':frames,'fps':fps,'changedBones':changed,'nativeFootMaxErrorDegrees':max(errors),'sourceSha256':hashlib.sha256(raw).hexdigest()})
        report['targets'].append({'operation':'overwrite','path':str(active),'beforeSha256':hashlib.sha256(old).hexdigest(),'candidate':str(candidate),'afterSha256':hashlib.sha256(new).hexdigest()})
assert len(report['clips'])==166
report['maxNativeFootErrorDegrees']=max(x['nativeFootMaxErrorDegrees'] for x in report['clips'])
with (HERE/'all-native-channels.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'clips':166,'frames':sum(x['frames'] for x in report['clips']),'maxNativeFootErrorDegrees':report['maxNativeFootErrorDegrees'],'otherChannelsByteIdentical':True,'liveFilesChanged':False},ensure_ascii=False))
