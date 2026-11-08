"""Bind native world-space poses to the existing PMX rest frames, without muscles.

Only writes an isolated candidate. Active resources are installed separately.
"""
from pathlib import Path
import json
import struct
import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path('H:/MGFR')
RELEASE = ROOT/'DialogueRenderRepair-20261020/Final-v3'
HERE = Path(__file__).resolve().parent
OUT = HERE/'native-reference-v2'
DATA = ROOT/'SiLLMBridge-20261020/MainData'

def mul(a,b):
    av,aw=a[...,:3],a[...,3:]
    bv,bw=b[...,:3],b[...,3:]
    return np.concatenate((aw*bv+bw*av+np.cross(av,bv),aw*bw-np.sum(av*bv,axis=-1,keepdims=True)),axis=-1)

def inv(q):
    return q*np.array([-1,-1,-1,1])

def apply(q,p):
    v=q[...,:3]
    return p+2*np.cross(v,np.cross(v,p)+q[...,3:]*p)

def align(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    q=np.r_[np.cross(a,b),1+np.dot(a,b)]
    if np.linalg.norm(q)<1e-8:
        axis=np.cross(a,[0,1,0])
        if np.linalg.norm(axis)<1e-8:axis=np.cross(a,[0,0,1])
        q=np.r_[axis,0]
    return q/np.linalg.norm(q)

def fk(nodes,local_q,local_p,needed):
    qs={};ps={}
    def visit(i):
        if i in qs:return
        parent=nodes[i]['parent']
        if parent>=0:
            visit(parent)
            qs[i]=mul(qs[parent],local_q[:,i])
            ps[i]=ps[parent]+apply(qs[parent],local_p[:,i])
        else:qs[i]=local_q[:,i];ps[i]=local_p[:,i]
    for i in needed:visit(i)
    return qs,ps

def main():
    OUT.mkdir(exist_ok=False)
    rig=json.loads((DATA/'source-rig.json').read_text(encoding='utf-8'))['nodes']
    names={n['name']:i for i,n in enumerate(rig)}
    manifest=json.loads((DATA/'motions/manifest.json').read_text(encoding='utf-8'))['clips']
    humans=['Hips','Spine','Chest','UpperChest','Neck','Head','LeftShoulder','LeftUpperArm','LeftLowerArm','LeftHand','RightShoulder','RightUpperArm','RightLowerArm','RightHand','LeftUpperLeg','LeftLowerLeg','LeftFoot','LeftToes','RightUpperLeg','RightLowerLeg','RightFoot','RightToes']
    sources=['Bip001_Pelvis','Bip001_Spine','Bip001_Spine1','Bip001_Spine2','Bip001_Neck','Bip001_Head','Bip001_L_Clavicle','Bip001_L_UpperArm','Bip001_L_Forearm','Bip001_L_Hand','Bip001_R_Clavicle','Bip001_R_UpperArm','Bip001_R_Forearm','Bip001_R_Hand','Bip001_L_Thigh','Bip001_L_Calf','Bip001_L_Foot','Bip001_L_Toe0','Bip001_R_Thigh','Bip001_R_Calf','Bip001_R_Foot','Bip001_R_Toe0']
    targets=['腰','上半身','上半身1','上半身2','首','頭','左肩','左腕','左ひじ','左手首','右肩','右腕','右ひじ','右手首','左足','左ひざ','左足首','左つま先','右足','右ひざ','右足首','右つま先']
    for side,jp in [('L','左'),('R','右')]:
        for f,part in enumerate(['親指','人指','中指','薬指','小指']):
            for j in range(3):
                humans.append(side+str(f)+str(j))
                sources.append('Bip001_'+side+'_Finger'+str(f)+('' if j==0 else str(j)))
                targets.append(jp+part+'０１２３'[j if f==0 else j+1])
    source_ids=[names[n] for n in sources]
    c=np.array([0.,1.,0.,0.])
    restq=np.array([[n['q'] for n in rig]],dtype=float)
    restp=np.array([[n['t'] for n in rig]],dtype=float)
    sq,sp=fk(rig,restq,restp,source_ids)
    source_rest_q={i:mul(c,sq[i][0]) for i in source_ids}
    source_rest_p={i:apply(c,sp[i][0]) for i in source_ids}
    report={'method':'native world-space reference-frame binding; no HumanPoseHandler, no muscle limits, no arbitrary shoulder/chest offsets','skins':{},'clips':[]}
    for skin,relative in [('swimsuit','skins/si-swimsuit-barefoot-ankle-v4/si_model.json'),('original','si/si_model.json')]:
        bones=json.loads((RELEASE/'Player/MGFR_Data/StreamingAssets'/relative).read_text(encoding='utf-8'))['bones']
        # Original appearance uses the original-skin rest model, not the bootstrap.
        if skin=='original':
            original=RELEASE/'Player/MGFR_Data/StreamingAssets/skins/si-original/si_model.json'
            if original.exists():bones=json.loads(original.read_text(encoding='utf-8'))['bones']
            elif bones[17]['positionScaled'][1]>=3:
                # Mirror ExperienceBootstrap.CalibrateRest for the legacy export.
                absolute=np.array([b['localScaled'] for b in bones],dtype=float)
                for i,b in enumerate(bones):
                    b['localScaled']=(absolute[i]-(absolute[b['parent']] if b['parent']>=0 else 0)).tolist()
                    b['positionScaled']=absolute[i].tolist()
        target_names={n['name']:i for i,n in enumerate(bones)}
        target_ids=[target_names[n] for n in targets]
        bind_q=np.tile([0.,0.,0.,1.],(1,len(bones),1))
        bind_p=np.array([[b['localScaled'] for b in bones]],dtype=float)
        _,tp=fk(bones,bind_q,bind_p,target_ids)
        calibration={i:np.array([0.,0.,0.,1.]) for i in target_ids}
        # The target skin's A-pose offsets are a different rest frame from native T.
        # Define each limb's rest frame from the matching anatomical segment.
        links=[(6,7),(7,8),(8,9),(10,11),(11,12),(12,13),(14,15),(15,16),(16,17),(18,19),(19,20),(20,21)]
        for k,child in links:
            ti,si=target_ids[k],source_ids[k]
            calibration[ti]=align(tp[target_ids[child]][0]-tp[ti][0],source_rest_p[source_ids[child]]-source_rest_p[si])
        for side in range(2):
            hand=9 if side==0 else 13
            middle=22+side*15+6
            calibration[target_ids[hand]]=align(tp[target_ids[middle]][0]-tp[target_ids[hand]][0],source_rest_p[source_ids[middle]]-source_rest_p[source_ids[hand]])
            for f in range(5):
                first=22+side*15+f*3
                for j in range(2):
                    k=first+j;child=k+1
                    calibration[target_ids[k]]=align(tp[target_ids[child]][0]-tp[target_ids[k]][0],source_rest_p[source_ids[child]]-source_rest_p[source_ids[k]])
                calibration[target_ids[first+2]]=calibration[target_ids[first+1]].copy()
        report['skins'][skin]={'bones':len(bones),'mapped':len(target_ids),'calibrationDegrees':{targets[k]:float(np.degrees(Rotation.from_quat(calibration[i]).magnitude())) for k,i in enumerate(target_ids[:22])}}
        dest=OUT/skin;dest.mkdir()
        for info in manifest:
            oldpath=RELEASE/'Player/MGFR_Data/StreamingAssets/native-actions'/skin/(info['name']+'.hpose')
            raw=oldpath.read_bytes();magic,count,frames,fps=struct.unpack_from('<iiif',raw)
            ids=np.frombuffer(raw,dtype='<i4',count=count,offset=16).copy()
            values=np.frombuffer(raw,dtype='<f4',offset=16+4*count).reshape(frames,count,7).copy()
            motion=(DATA/'motions'/info['file']).read_bytes()
            n,nf,rate=struct.unpack_from('<iif',motion,8)
            assert (n,nf,rate)==(len(rig),frames,fps)
            samples=np.frombuffer(motion,dtype='<f4',offset=20).reshape(frames,n,10)
            q,p=fk(rig,samples[:,:,:4],samples[:,:,4:7],source_ids)
            desired={ti:mul(mul(mul(c,q[si]),inv(source_rest_q[si])),calibration[ti]) for ti,si in zip(target_ids,source_ids)}
            index={int(i):k for k,i in enumerate(ids)}
            for ti in target_ids:
                parent=bones[ti]['parent']
                while parent>=0 and parent not in desired:parent=bones[parent]['parent']
                local=mul(inv(desired[parent]),desired[ti]) if parent>=0 else desired[ti]
                values[:,index[ti],3:]=local
            for aux,main in zip([738,739,740,742,743,744],[25,26,27,21,22,23]):values[:,index[aux],3:]=values[:,index[main],3:]
            # Retain the established per-skin planted root trajectory and joint lengths.
            assert np.isfinite(values).all()
            norms=np.linalg.norm(values[:,:,3:],axis=-1)
            assert np.max(np.abs(norms-1))<1e-4
            path=dest/(info['name']+'.hpose')
            with path.open('xb') as f:f.write(raw[:16+4*count]);f.write(values.astype('<f4').tobytes())
            # Independent forward-kinematics comparison on torso and arm endpoints.
            tq=np.tile([0.,0.,0.,1.],(frames,len(bones),1));tpos=np.broadcast_to(bind_p,(frames,len(bones),3)).copy()
            tq[:,ids]=values[:,:,3:];tpos[:,ids]=values[:,:,:3]
            _,positions=fk(bones,tq,tpos,target_ids)
            bq=np.tile([0.,0.,0.,1.],(frames,len(bones),1));bp=np.broadcast_to(bind_p,(frames,len(bones),3)).copy()
            before=np.frombuffer(raw,dtype='<f4',offset=16+4*count).reshape(frames,count,7)
            bq[:,ids]=before[:,:,3:];bp[:,ids]=before[:,:,:3]
            _,oldpos=fk(bones,bq,bp,target_ids)
            errors={}
            for k in [4,7,8,9,11,12,13]:
                ti,si=target_ids[k],source_ids[k]
                reference=apply(c,p[si]-p[source_ids[4]])
                actual=positions[ti]-positions[target_ids[4]]
                previous=oldpos[ti]-oldpos[target_ids[4]]
                errors[targets[k]]={'beforeMeanM':float(np.mean(np.linalg.norm(previous-reference,axis=-1))),'afterMeanM':float(np.mean(np.linalg.norm(actual-reference,axis=-1)))}
            report['clips'].append({'name':info['name'],'skin':skin,'frames':frames,'positionErrors':errors})
    with (OUT/'report.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({'clips':len(report['clips']),'output':str(OUT)},ensure_ascii=False))

if __name__=='__main__':main()
