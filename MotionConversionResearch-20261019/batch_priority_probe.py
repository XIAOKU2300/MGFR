"""Bounded batch feasibility run for idle/walk/cute candidates, not deployment."""
from pathlib import Path
import json,struct,subprocess,time
ROOT=Path(__file__).resolve().parent;DATA=Path('H:/MGFR/SiMotions-20261019')
OUT=ROOT/'priority-batch-probe-v1';OUT.mkdir(exist_ok=False)
native=json.loads((ROOT/'solver-probe-v1/native-muscles.json').read_text(encoding='utf-8'))['names']
attributes={7*i+j:part+suffix for i,part in enumerate(['Motion','Root','LeftFoot','RightFoot','LeftHand','RightHand']) for j,suffix in enumerate(['T.x','T.y','T.z','Q.x','Q.y','Q.z','Q.w'])}
attributes.update({42+i:n for i,n in enumerate(native)})
allrows=[]
for sub,listfile in [('', 'reports/clips.json'),('controller-linked','controller-linked/clips.json')]:
 for row in json.loads((DATA/listfile).read_text(encoding='utf-8')):allrows.append((DATA/sub,row))
names=['A_actor_girl_idle_loop','A_actor_jsspsi_relax_loop','A_actor_jsspsi_relax_sp_01','A_actor_jsspsi_relax_sp_02','A_actor_girl_walk_loop','A_actor_jsspsi_walk_loop_sp_01','A_actor_jsspsi_interact_receive_gift','A_actor_jsspsi_dialog_single_tsundere','A_actor_jsspsi_dialog_single_play','A_actor_jsspsi_interact_camera_01','A_actor_jsspsi_dialog_virtual_single_idle_nod','A_actor_jsspsi_dialog_virtual_single_idle_shake','A_actor_jsspsi_dialog_virtual_state_scratchhead_loop']
results=[];begin=time.perf_counter()
for name in names:
 start=time.perf_counter();record={'name':name,'status':'failed'}
 try:
  base,row=next((b,r) for b,r in allrows if r['name']==name)
  clip=json.loads((base/row['decoded']).read_text(encoding='utf-8'))
  samples=base/'sampled-curves'/(Path(row['acl_buffers']['FloatBufferData']['path']).name+'.samples')
  with samples.open('rb') as f:header=struct.unpack('<8sBHIIff',f.read(27))
  scalar=[b for b in clip['m_ClipBindingConstant']['genericBindings'] if b['typeID']!=4 and not b['isPPtrCurve']]
  if len(scalar)!=header[3]:raise ValueError(f'scalar binding mismatch {len(scalar)} vs {header[3]}')
  channels={attributes[b['attribute']]:i for i,b in enumerate(scalar) if b['typeID']==95 and b['customType']==8 and b['attribute'] in attributes}
  if not any(k.startswith('RootT.') for k in channels):raise ValueError('No root translation channels; needs other-track/default reconstruction')
  manifest=OUT/(name+'.channels.json')
  with manifest.open('x',encoding='utf-8') as f:json.dump(channels,f,indent=2)
  dest=OUT/(name+'.body.json')
  result=subprocess.run(['C:/Program Files/dotnet/dotnet.exe',str(ROOT/'solver-probe-v1/Probe.dll'),str(ROOT/'source-avatar.json'),str(manifest),str(samples),str(dest)],capture_output=True,text=True)
  if result.returncode:raise ValueError('Math solver rejected input')
  solved=json.loads(dest.read_text(encoding='utf-8'))
  record.update(status='math-probe-passed',frames=solved['frames'],fps=solved['fps'],duration=solved['duration'],result=str(dest),channel_count=len(channels),visual_validated=False)
 except (ValueError,KeyError,StopIteration,FileNotFoundError) as e:record['reason']=str(e) or 'not found'
 record['seconds']=time.perf_counter()-start;results.append(record);print(name,record['status'],record.get('reason',''))
report={'status':'research probes, not finished retargeted motions','limitations':['Six native custom foot/toe channels omitted','No target-model playback validation','Do not treat additive/virtual names as independent playback approval'],'elapsed_seconds':time.perf_counter()-begin,'clips':results}
with (OUT/'report.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print('elapsed',report['elapsed_seconds'])
