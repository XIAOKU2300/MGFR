"""Combine decoded native transform tracks and solved humanoid tracks."""
from pathlib import Path
import json,struct,base64,numpy as np
ROOT=Path(__file__).resolve().parent;RESEARCH=Path('H:/MGFR/MotionConversionResearch-20261019');DATA=Path('H:/MGFR/SiMotions-20261019')
OUT=ROOT/'motions-v2';OUT.mkdir(exist_ok=False)
model=json.loads((ROOT/'assets-v1/native-model.json').read_text(encoding='utf-8'))
avatar=json.loads((RESEARCH/'source-avatar.json').read_text(encoding='utf-8'))
path_index={n['path']:i for i,n in enumerate(model['nodes'])};hash_index={h:i for i,h in enumerate(avatar['m_Avatar']['m_AvatarSkeleton']['data']['m_ID'])}
rest=np.array([n['q']+n['t']+n['s'] for n in model['nodes']],dtype='<f4')
rows=[]
for base,listfile in [(DATA,'reports/clips.json'),(DATA/'controller-linked','clips.json')]:
 for row in json.loads((base/listfile).read_text(encoding='utf-8')):rows.append((base,row))
names={'dialog_state_idle_loop':'Stand idle','dialog_single_wave':'Wave','dialog_virtual_single_walk_m':'Walk and settle','relax_loop':'Relaxed idle','relax_sp_01':'Special idle 1','relax_sp_02':'Special idle 2','interact_receive_gift':'Receive gift','dialog_single_tsundere':'Tsundere','dialog_single_play':'Play','interact_camera_01':'Camera pose','dialog_virtual_single_idle_nod':'Nod','dialog_virtual_single_idle_shake':'Shake head','dialog_virtual_state_scratchhead_loop':'Scratch head','walk_loop_sp_01':'Character walk variation','A_actor_girl_idle_loop':'Base idle','A_actor_girl_walk_loop':'Base walk'}
manifest=[];errors=[]
for folder in ['focused-probe-v2','priority-batch-probe-v1']:
 for source in sorted((RESEARCH/folder).glob('*.body.json')):
  name=source.name.removesuffix('.body.json')
  try:
   body=json.loads(source.read_text(encoding='utf-8'));frames=body['frames'];fps=body['fps']
   base,row=next((b,r) for b,r in rows if r['name']==name)
   clip=json.loads((base/row['decoded']).read_text(encoding='utf-8'));bindings=clip['m_ClipBindingConstant']['genericBindings']
   positions=[b for b in bindings if b['typeID']==4 and b['attribute']==1];rotations=[b for b in bindings if b['typeID']==4 and b['attribute']==2]
   track_paths=[b['path'] for b in rotations]
   assert len(track_paths)==clip['m_AclCompressedBuffer']['OutputTrackCount'] and len(set(track_paths))==len(track_paths)
   masks=base64.b64decode(clip['m_AclCompressedBuffer']['TransformSubTrackMasks']['data']);group=(len(track_paths)+7)//8
   def present(component,index):return bool(masks[component*group+index//8] & (1<<(7-index%8)))
   for component,attribute in enumerate([1,2,3]):
    actual={b['path'] for b in bindings if b['typeID']==4 and b['attribute']==attribute}
    assert {h for i,h in enumerate(track_paths) if present(component,i)}==actual
   transforms=base/'sampled-curves'/(Path(row['acl_buffers']['TransformBufferData']['path']).name+'.samples')
   raw=transforms.read_bytes();header=struct.unpack_from('<8sBHIIff',raw)
   assert header[1]==12 and header[3]==len(track_paths) and header[4]==frames
   values=np.frombuffer(raw,dtype='<f4',offset=27).reshape(frames,len(track_paths),10)
   output=np.broadcast_to(rest,(frames,*rest.shape)).copy();unmatched=[]
   for i,path in enumerate(track_paths):
    index=hash_index.get(path)
    if index is None:unmatched.append(path);continue
    if present(0,i):output[:,index,4:7]=values[:,i,4:7]
    if present(1,i):output[:,index,:4]=values[:,i,:4]
    if present(2,i):output[:,index,7:10]=values[:,i,7:10]
   for i,bone in enumerate(body['bones']):output[:,path_index[bone['Path']],:4]=[f['rotations'][i] for f in body['samples']]
   hips=path_index[next(b['Path'] for b in body['bones'] if b['Slot']==0)]
   output[:,hips,4:7]=[f['hips'] for f in body['samples']]
   output[:,0,:4]=[f['motionQ'] for f in body['samples']];output[:,0,4:7]=[f['motionT'] for f in body['samples']]
   assert np.isfinite(output).all()
   q=output[:,:,:4];q/=np.maximum(np.linalg.norm(q,axis=-1,keepdims=True),1e-20)
   for f in range(1,frames):q[f,np.sum(q[f-1]*q[f],axis=-1)<0]*=-1
   dest=OUT/(name+'.motion');
   with dest.open('xb') as f:f.write(struct.pack('<8sIIf',b'ENFMOT1\0',len(rest),frames,fps));f.write(output.astype('<f4').tobytes())
   suffix=name.removeprefix('A_actor_jsspsi_');label=names.get(name,names.get(suffix,suffix))
   manifest.append({'name':name,'label':label,'file':dest.name,'frames':frames,'fps':fps,'duration':(frames-1)/fps,'unmatched_transform_paths':unmatched,'loop':bool(clip['m_MuscleClip']['m_LoopTime']),'source_clip':str(base/row['decoded'])})
   print(name,'frames',frames,'unmatched',len(unmatched))
  except (ValueError,KeyError,AssertionError) as e:errors.append({'name':name,'error':str(e)})
with (OUT/'manifest.json').open('x',encoding='utf-8') as f:json.dump({'format':'ENFMOT1','notes':['Native source rig, not MGFR.','Custom foot/toe axes not yet applied in v1.','Generic channels from other character rigs are listed as unmatched.'],'clips':manifest,'errors':errors},f,indent=2)
print('RESULT',len(manifest),'passed',len(errors),'errors')
