from pathlib import Path
import json,struct,subprocess,time
ROOT=Path('H:/MGFR/EndfieldNativeMotions-20261019');DATA=Path('H:/MGFR/SiMotions-20261019');EXPANSION=Path(__file__).resolve().parent;OUT=EXPANSION/'body-solved-v2';OUT.mkdir(exist_ok=False)
names=['A_actor_jsspsi_dialog_virtual_state_introduction_loop', 'A_actor_jsspsi_dialog_virtual_single_idle_talkhands', 'A_actor_jsspsi_dialog_virtual_state_think1_loop', 'A_actor_jsspsi_dialog_virtual_state_scratchhead_start', 'A_actor_jsspsi_dialog_state_surprise_loop', 'A_actor_jsspsi_dialog_state_chesthugging1_loop', 'A_actor_jsspsi_dialog_state_point_loop', 'A_actor_jsspsi_dialog_state_muse_loop', 'A_actor_jsspsi_relax_react', 'A_actor_jsspsi_idle_to_relax']
native=json.loads((ROOT/'solver-v2/native-muscles.json').read_text(encoding='utf-8'))['names']
attributes={7*i+j:part+suffix for i,part in enumerate(['Motion','Root','LeftFoot','RightFoot','LeftHand','RightHand']) for j,suffix in enumerate(['T.x','T.y','T.z','Q.x','Q.y','Q.z','Q.w'])};attributes.update({42+i:n for i,n in enumerate(native)})
rows=[]
for base,listfile in [(DATA,'reports/clips.json'),(DATA/'controller-linked','clips.json')]:
 for r in json.loads((base/listfile).read_text(encoding='utf-8')):rows.append((base,r))
reports=[];start=time.perf_counter()
for name in names:
 base,row=next((b,r) for b,r in rows if r['name']==name);clip=json.loads((base/row['decoded']).read_text(encoding='utf-8'));sample=base/'sampled-curves'/(Path(row['acl_buffers']['FloatBufferData']['path']).name+'.samples')
 with sample.open('rb') as f:header=struct.unpack('<8sBHIIff',f.read(27))
 scalar=[b for b in clip['m_ClipBindingConstant']['genericBindings'] if b['typeID']!=4 and not b['isPPtrCurve']];assert len(scalar)==header[3]
 channels={attributes[b['attribute']]:i for i,b in enumerate(scalar) if b['typeID']==95 and b['customType']==8 and b['attribute'] in attributes};manifest=OUT/(name+'.channels.json')
 with manifest.open('x',encoding='utf-8') as f:json.dump(channels,f,indent=2)
 target=OUT/(name+'.body.json');result=subprocess.run(['C:/Program Files/dotnet/dotnet.exe',str(ROOT/'solver-v2/Probe.dll'),'H:/MGFR/MotionConversionResearch-20261019/source-avatar.json',str(manifest),str(sample),str(target)],capture_output=True,text=True)
 if result.returncode:raise ValueError('Solver rejected '+name)
 reports.append({'name':name,'frames':header[4],'native_custom_axes_bound':[n for n in ['Left Foot Twist Roll','Right Foot Twist Roll','Left Toes Left-Right','Right Toes Left-Right','Left Toes Twist Roll','Right Toes Twist Roll'] if n in channels]});print(name,'OK',flush=True)
with (OUT/'report.json').open('x',encoding='utf-8') as f:json.dump({'elapsed_seconds':time.perf_counter()-start,'clips':reports},f,indent=2)
