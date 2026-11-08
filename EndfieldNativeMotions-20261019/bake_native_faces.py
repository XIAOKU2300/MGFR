"""Bake selected original facial controls on the original source skeleton.
Emotion hold/fade timing is authored for preview; facial deltas are game data.
"""
from pathlib import Path
import json,struct,zlib,shutil,numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'motions-v3';OUT.mkdir(exist_ok=False)
model=json.loads((ROOT/'assets-v1/native-model.json').read_text(encoding='utf-8'))
avatar=json.loads((ROOT/'face-sources-v1/native-face-avatar-decoded.json').read_text(encoding='utf-8'))
data=avatar['data'];refs={x['rid']:x['data'] for x in avatar['references']['RefIds']}
mapping={n:refs[r['rid']] for n,r in zip(data['morphMappingNames'],data['morphMappingCfgs'])}
lookup={zlib.crc32(n['name'].encode()):i for i,n in enumerate(model['nodes'])}
base={b['boneNameHash']&0xffffffff:b for b in data['basePoseConfig']}
assert len(base)==97 and all(k in lookup for k in base)
def v(o):return np.array([o[c] for c in 'xyz'],dtype=np.float64)
def rotation(euler):return Rotation.from_euler('xyz',np.asarray(euler)*[1,-1,-1],degrees=True).as_quat()
baseline_errors=[np.degrees((Rotation.from_quat(rotation(v(b['rotation']))).inv()*Rotation.from_quat(model['nodes'][lookup[k]]['q'])).magnitude()) for k,b in base.items()]
assert max(baseline_errors)<.003
manifest=json.loads((ROOT/'motions-v2/manifest.json').read_text(encoding='utf-8'))
for clip in manifest['clips']:
 target=OUT/clip['file']
 with target.open('xb') as f:f.write((ROOT/'motions-v2'/clip['file']).read_bytes())
idle=ROOT/'motions-v2/A_actor_jsspsi_dialog_state_idle_loop.motion';raw=idle.read_bytes();_,nodes,frames,fps=struct.unpack_from('<8sIIf',raw)
idle_values=np.frombuffer(raw,dtype='<f4',offset=20).reshape(frames,nodes,10)
presets=[]
selected=[('happys','Soft smile'),('happym','Happy'),('happyl','Big smile'),('shya','Shy'),('happysquinta','Squint smile'),('favoura','Affection')]
for suffix,label in selected:
 files=[p for sub in ['face-sources-v1','face-sources-v2'] for p in (ROOT/sub).glob('data_facialmorph_emotion_'+suffix+'_*.json')]
 assert len(files)==1
 emotion=json.loads(files[0].read_text(encoding='utf-8'));weights={item['_ctrlName']:item['_value'] for k,items in emotion['_pose'].items() if isinstance(items,list) for item in items}
 assert all(name in mapping for name in weights)
 presets.append({'name':'face_'+suffix,'label':label,'source':str(files[0]),'weights':weights})
blink_file=next((ROOT/'face-sources-v2').glob('data_facialmorph_anim_blink_02_*.json'));blink=json.loads(blink_file.read_text(encoding='utf-8'))
blink_curves={row['_ctrlName']:row['_curve']['m_Curve'] for rows in blink.values() if isinstance(rows,list) for row in rows if '_curve' in row}
assert all(n in mapping for n in blink_curves)
assert all(k['weightedMode']==0 for keys in blink_curves.values() for k in keys)
presets.extend([{'name':'face_blink','label':'Blink','source':str(blink_file),'curves':blink_curves},{'name':'face_wink_left','label':'Wink left (composed)','source':str(blink_file),'curves':{n:keys for n,keys in blink_curves.items() if '_L_ctrl' in n}}])
def hermite(keys,t):
 if t<=keys[0]['time']:return keys[0]['value']
 if t>=keys[-1]['time']:return keys[-1]['value']
 for a,b in zip(keys,keys[1:]):
  if a['time']<=t<=b['time']:
   dt=b['time']-a['time'];u=(t-a['time'])/dt
   return (2*u**3-3*u*u+1)*a['value']+(u**3-2*u*u+u)*dt*a['outSlope']+(-2*u**3+3*u*u)*b['value']+(u**3-u*u)*dt*b['inSlope']
 raise ValueError('curve interval')
reports=[]
for preset in presets:
 count=181;output=idle_values[np.arange(count)%(frames-1)].copy();changed=set()
 for frame in range(count):
  t=frame/60
  if 'curves' in preset:weights={n:hermite(keys,t-1) for n,keys in preset['curves'].items()}
  else:
   weight=np.clip(min(t/.5,(3-t)/.5),0,1);weight=weight*weight*(3-2*weight);weights={n:w*weight for n,w in preset['weights'].items()}
  deltas={k:[np.zeros(3),np.zeros(3),np.zeros(3)] for k in base}
  for name,weight in weights.items():
   if abs(weight)<1e-12:continue
   for b in mapping[name]['bones']:
    key=b['boneNameHash']&0xffffffff;assert key in base
    for j,field in enumerate(['position','rotation','scale']):deltas[key][j]+=v(b[field])*weight
    changed.add(lookup[key])
  for key,b in base.items():
   index=lookup[key];dp,dr,ds=deltas[key]
   output[frame,index,:4]=rotation(v(b['rotation'])+dr)
   output[frame,index,4:7]=v(b['position'])+dp;output[frame,index,7:10]=v(b['scale'])+ds
 assert np.isfinite(output).all()
 for frame in range(1,count):output[frame,np.sum(output[frame-1,:,:4]*output[frame,:,:4],axis=1)<0,:4]*=-1
 name=preset['name']+'.motion'
 with (OUT/name).open('xb') as f:f.write(struct.pack('<8sIIf',b'ENFMOT1\0',nodes,count,60));f.write(output.astype('<f4').tobytes())
 manifest['clips'].append({'name':preset['name'],'label':preset['label'],'file':name,'frames':count,'fps':60,'duration':3,'loop':True,'source_face':preset['source'],'authored_composition':True})
 reports.append({'name':preset['name'],'label':preset['label'],'changed_face_bones':len(changed),'source':preset['source']})
 print(preset['name'],len(changed),'affected bones')
manifest['notes']+=['Face clips use original character-specific deltas. Emotion transitions/idle backing and one-sided wink are preview compositions.','Native generic blink 01 contains obsolete controller names and is intentionally not applied. Blink 02 matches the source character controls.']
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
with (ROOT/'face-calibration-v1.json').open('x',encoding='utf-8') as f:json.dump({'source_face_bones':len(base),'maximum_rest_rotation_error_degrees':max(baseline_errors),'euler_mapping':'extrinsic xyz with signs (+,-,-); empirically checked against all 97 native rest quaternions','clips':reports},f,indent=2)
print('TOTAL',len(manifest['clips']))
