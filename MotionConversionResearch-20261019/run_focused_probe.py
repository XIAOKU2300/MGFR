"""Solve three priority motions with explicit bindings; fail on schema mismatches."""
from pathlib import Path
import json,struct,subprocess,time
import numpy as np
ROOT=Path(__file__).resolve().parent
DATA=Path('H:/MGFR/SiMotions-20261019')
OUT=ROOT/'focused-probe-v1'
OUT.mkdir(exist_ok=False)
native=json.loads((ROOT/'solver-probe-v1/native-muscles.json').read_text(encoding='utf-8'))['names']
attributes={}
for i,part in enumerate(['Motion','Root','LeftFoot','RightFoot','LeftHand','RightHand']):
    for j,suffix in enumerate(['T.x','T.y','T.z','Q.x','Q.y','Q.z','Q.w']):attributes[i*7+j]=part+suffix
attributes.update({42+i:n for i,n in enumerate(native)})
for hand in range(2):
    for finger,name in enumerate(['Thumb','Index','Middle','Ring','Little']):
        for j,suffix in enumerate(['1 Stretched','Spread','2 Stretched','3 Stretched']):
            attributes[103+hand*20+finger*4+j]=f'{["LeftHand","RightHand"][hand]}.{name}.{suffix}'
allrows=[]
for sub,listfile in [('', 'reports/clips.json'),('controller-linked','controller-linked/clips.json')]:
    for row in json.loads((DATA/listfile).read_text(encoding='utf-8')):allrows.append((DATA/sub,row))
names=['A_actor_jsspsi_dialog_state_idle_loop','A_actor_jsspsi_dialog_single_wave','A_actor_jsspsi_dialog_virtual_single_walk_m']
report=[]
for name in names:
    base,row=next((b,r) for b,r in allrows if r['name']==name)
    clip=json.loads((base/row['decoded']).read_text(encoding='utf-8'))
    samples=base/'sampled-curves'/(Path(row['acl_buffers']['FloatBufferData']).name+'.samples')
    raw=samples.read_bytes();magic,typ,ver,tracks,frames,fps,duration=struct.unpack_from('<8sBHIIff',raw)
    assert magic==b'ACLBAKE1' and typ==0
    scalar=[b for b in clip['m_ClipBindingConstant']['genericBindings'] if b['typeID']!=4 and not b['isPPtrCurve']]
    assert len(scalar)==tracks,(name,len(scalar),tracks)
    channels={attributes[b['attribute']]:i for i,b in enumerate(scalar) if b['typeID']==95 and b['customType']==8 and b['attribute'] in attributes}
    manifest=OUT/(name+'.channels.json')
    with manifest.open('x',encoding='utf-8') as f:json.dump(channels,f,indent=2)
    values=np.frombuffer(raw,dtype='<f4',offset=27).reshape(frames,tracks)
    extra={n:[float(values[:,channels[n]].min()),float(values[:,channels[n]].max())] for i,n in enumerate(native) if i in [28,30,31,39,41,42] and n in channels}
    dest=OUT/(name+'.body.json');start=time.perf_counter()
    result=subprocess.run(['C:/Program Files/dotnet/dotnet.exe',str(ROOT/'solver-probe-v1/Probe.dll'),str(ROOT/'source-avatar.json'),str(manifest),str(samples),str(dest)],capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stderr)
    elapsed=time.perf_counter()-start
    report.append({'name':name,'frames':frames,'fps':fps,'duration':duration,'seconds':elapsed,'extra_dof_ranges':extra,'clip':str(base/row['decoded']),'scalar_samples':str(samples),'body_result':str(dest),'known_limitation':'Six custom foot/toe DOFs not applied in math probe v1; exact native axis mapping still under investigation.'})
    print(name,result.stdout.strip(),f'{elapsed:.3f}s')
with (OUT/'report.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
