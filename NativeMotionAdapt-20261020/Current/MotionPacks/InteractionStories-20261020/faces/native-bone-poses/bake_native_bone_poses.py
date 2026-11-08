"""Bake the selected source emotion _pose deltas into ENFMOT1 clips.
Only reads checked-in native model/source evidence; output files are exclusive-create.
"""
import json, hashlib, math, struct, zlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(r'H:\MGFR')
OUT=ROOT/'NativeMotionAdapt-20261020/Current/MotionPacks/InteractionStories-20261020/faces/native-bone-poses'
if any(OUT.iterdir()): raise SystemExit(f'Refusing non-empty output directory: {OUT}')
def readj(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def writej(path,obj):
    with path.open('x',encoding='utf-8',newline='\n') as f: json.dump(obj,f,ensure_ascii=False,indent=2); f.write('\n')
def vec(obj): return np.asarray([obj[k] for k in 'xyz'],dtype=np.float64)
def quat_from_euler(deg): return Rotation.from_euler('xyz',np.asarray(deg,dtype=float)*[1,-1,-1],degrees=True).as_quat()
def qnorm(a): return np.linalg.norm(a,axis=-1)
PARENT=OUT.parent
selected=readj(PARENT/'native-presets.json')['presets']
if len(selected)!=12: raise ValueError(f'Expected 12 selected presets, got {len(selected)}')
source_root=ROOT/'SiLLMBridge-20261020/emotion-expansion/source'
model_root=ROOT/'EndfieldNativeMotions-20261019'
model=readj(model_root/'assets-v1/native-model.json')
avatar=readj(model_root/'face-sources-v1/native-face-avatar-decoded.json')
data=avatar['data']; refs={x['rid']:x['data'] for x in avatar['references']['RefIds']}
names=data['morphMappingNames']; cfgs=data['morphMappingCfgs']
if len(names)!=len(cfgs) or len(set(names))!=len(names): raise ValueError('Control mapping names/configs mismatch or duplicate names')
mapping={n:refs[r['rid']] for n,r in zip(names,cfgs)}
lookup={zlib.crc32(node['name'].encode())&0xffffffff:i for i,node in enumerate(model['nodes'])}
base={b['boneNameHash']&0xffffffff:b for b in data['basePoseConfig']}
if len(base)!=97 or any(k not in lookup for k in base): raise ValueError('Face skeleton must map all 97 cfg bones')
node_count=len(model['nodes'])
if node_count!=596: raise ValueError(f'Expected full 596-node model, got {node_count}')
errors=[math.degrees((Rotation.from_quat(quat_from_euler(vec(b['rotation']))).inv()*Rotation.from_quat(model['nodes'][lookup[k]]['q'])).magnitude()) for k,b in base.items()]
max_rest_error=max(errors)
if max_rest_error>=0.003: raise ValueError(f'Native rest pose mismatch: {max_rest_error} degrees')
if len({x['name'] for x in selected})!=12: raise ValueError('Selected source names are not unique')
clips=[]; motions=[]; source_pose_dedup={}; all_mapped=True
for preset in selected:
    name=preset['name']; src_name=Path(preset['source_file']).name; src_path=source_root/src_name
    raw_bytes=src_path.read_bytes(); source_hash=hashlib.sha256(raw_bytes).hexdigest()
    if source_hash.lower()!=preset['source_sha256'].lower(): raise ValueError(f'Source SHA mismatch: {name}')
    value=json.loads(raw_bytes.decode('utf-8-sig'))
    if value.get('_pose')!=preset.get('pose'): raise ValueError(f'Embedded source pose mismatch: {name}')
    byctrl={}
    for items in value.get('_pose',{}).values():
        if isinstance(items,list):
            for item in items:
                if isinstance(item,dict) and '_ctrlName' in item and '_value' in item:
                    control=item['_ctrlName']; weight=float(item['_value'])
                    byctrl[control]=byctrl.get(control,0.0)+weight
    supplied={k:float(v) for k,v in preset['ctrl_weights'].items()}
    if set(byctrl)!=set(supplied) or any(abs(byctrl[k]-supplied[k])>1e-8 for k in byctrl):
        raise ValueError(f'Extracted controls differ from candidate list: {name}')
    nonzero={k:w for k,w in byctrl.items() if abs(w)>1e-12}
    missing=sorted(k for k in nonzero if k not in mapping)
    if missing: all_mapped=False; raise ValueError(f'Unmapped controls for {name}: {missing}')
    delta={k:[np.zeros(3),np.zeros(3),np.zeros(3)] for k in base}
    for control,weight in nonzero.items():
        for bone in mapping[control]['bones']:
            key=bone['boneNameHash']&0xffffffff
            if key not in base: raise ValueError(f'Mapped bone outside 97-face cfg for {name}: {key:08x}')
            delta[key][0]+=vec(bone['position'])*weight
            delta[key][1]+=vec(bone['rotation'])*weight
            delta[key][2]+=vec(bone['scale'])*weight
    values=np.zeros((2,node_count,10),dtype=np.float64)
    for i,node in enumerate(model['nodes']):
        values[:,i,:4]=node['q']; values[:,i,4:7]=node['t']; values[:,i,7:10]=node['s']
    changed=[]
    for key,bone_cfg in base.items():
        i=lookup[key]; dp,dr,ds=delta[key]
        values[:,i,:4]=quat_from_euler(vec(bone_cfg['rotation'])+dr)
        values[:,i,4:7]=vec(bone_cfg['position'])+dp
        values[:,i,7:10]=vec(bone_cfg['scale'])+ds
        if np.linalg.norm(dp)+np.linalg.norm(dr)+np.linalg.norm(ds)>1e-8:
            changed.append(model['nodes'][i]['name'])
    if not changed: raise ValueError(f'Preset produced no face-bone delta: {name}')
    if not np.isfinite(values).all(): raise ValueError(f'Non-finite pose: {name}')
    norms=qnorm(values[:,:,:4])
    if not np.allclose(norms,1.0,atol=2e-5): raise ValueError(f'Invalid quaternion norm: {name}')
    if not np.array_equal(values[0],values[1]): raise ValueError(f'Frames are not fixed/equal: {name}')
    key=values[0].round(6).tobytes()
    if key in source_pose_dedup: raise ValueError(f'Pose duplicates {source_pose_dedup[key]}: {name}')
    source_pose_dedup[key]=name
    motion_name='face_interaction_'+name.removeprefix('data_facialmorph_emotion_')+'.motion'
    motion_path=OUT/motion_name
    with motion_path.open('xb') as f:
        f.write(struct.pack('<8sIIf',b'ENFMOT1\0',node_count,2,60.0))
        f.write(values.astype('<f4').tobytes())
    digest=hashlib.sha256(motion_path.read_bytes()).hexdigest()
    motions.append({'name':'face_interaction_'+name.removeprefix('data_facialmorph_emotion_'),'file':motion_name,'format':'ENFMOT1','frames':2,'fps':60,'duration':1/60,'source_preset':name,'source_file':src_name,'source_path':preset['source_path'],'source_sha256':source_hash,'motion_sha256':digest,'ctrl_weights':preset['ctrl_weights'],'aliases_same_nonzero_signature':preset['aliases_same_nonzero_signature'],'new_unique_preset':preset['new_unique_preset'],'changed_face_bones':len(changed),'changed_face_bone_names':changed})
manifest={'format':'ENFMOT1','node_count':node_count,'frames':2,'fps':60,'clip_count':len(motions),'purpose':'Original game preset face poses baked on the full native skeleton for archival/future adaptation only.','runtime_compatibility':False,'clips':motions}
writej(OUT/'manifest.json',manifest)
validation={'source_script':'SiLLMBridge-20261020/emotion-expansion/expand_emotions.py','conversion_scope':'Reused its original character mapping/rest contract and control-to-bone position/rotation/scale delta accumulation only; VFS extraction section was not run.','selected_native_presets':len(selected),'generated_clips':len(motions),'model_nodes':node_count,'face_cfg_bones':len(base),'face_cfg_bones_all_mapped_to_model':True,'nonzero_controls_all_mapped':all_mapped,'all_outputs_finite':True,'quaternion_norm_tolerance':2e-5,'all_quaternion_norms_valid':True,'rest_rotation_max_error_degrees':max_rest_error,'rest_rotation_limit_degrees_exclusive':0.003,'all_rest_rotations_within_limit':max_rest_error<0.003,'all_clips_have_changed_face_bones':all(x['changed_face_bones']>0 for x in motions),'all_fixed_two_frame_clips_equal':True,'all_pose_deltas_unique':True,'runtime_playable':False,'runtime_limit':'These are 596-node/97-face-bone native poses. Current player has 58 body bones and consumes PMX blendshape expressions; no adapter or body manifest entry was changed.','clips':[{'source_preset':x['source_preset'],'source_sha256':x['source_sha256'],'changed_face_bones':x['changed_face_bones'],'motion_sha256':x['motion_sha256']} for x in motions]}
writej(OUT/'validation.json',validation)
# Re-open and validate binary headers and expected payload sizes from files on disk.
for clip in motions:
    b=(OUT/clip['file']).read_bytes()
    magic,count,frames,fps=struct.unpack_from('<8sIIf',b,0)
    if (magic,count,frames)!=(b'ENFMOT1\0',596,2) or fps!=60.0 or len(b)!=20+2*596*10*4:
        raise ValueError('Invalid ENFMOT1 file layout: '+clip['file'])
print(json.dumps({'output':str(OUT),'clips':len(motions),'nodes':node_count,'face_bones':len(base),'rest_error_degrees':max_rest_error,'changed_face_bones':{x['source_preset']:x['changed_face_bones'] for x in motions}},ensure_ascii=False,indent=2))
