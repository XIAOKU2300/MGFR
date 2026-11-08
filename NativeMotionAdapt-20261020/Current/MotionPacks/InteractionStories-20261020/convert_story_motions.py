"""Additive, offline conversion. Never writes to an installed runtime or game."""
from pathlib import Path
import argparse, base64, hashlib, json, struct, subprocess, time, zlib
import numpy as np

ROOT = Path('H:/MGFR')
PACK = Path(__file__).resolve().parent
NATIVE = ROOT / 'EndfieldNativeMotions-20261019'

def save(path, data):
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run(selections, rows, output):
    output.mkdir(exist_ok=False)
    solved = output / 'body-solved'; solved.mkdir()
    motions = output / 'motions'; motions.mkdir()
    model = json.loads((NATIVE/'assets-v1/native-model.json').read_text(encoding='utf-8'))
    avatar = json.loads((ROOT/'MotionConversionResearch-20261019/source-avatar.json').read_text(encoding='utf-8'))
    muscles = json.loads((NATIVE/'solver-v2/native-muscles.json').read_text(encoding='utf-8'))['names']
    attributes = {7*i+j:part+suffix for i,part in enumerate(['Motion','Root','LeftFoot','RightFoot','LeftHand','RightHand']) for j,suffix in enumerate(['T.x','T.y','T.z','Q.x','Q.y','Q.z','Q.w'])}
    attributes.update({42+i:n for i,n in enumerate(muscles)})
    paths = {n['path']:i for i,n in enumerate(model['nodes'])}
    hashes = {h:i for i,h in enumerate(avatar['m_Avatar']['m_AvatarSkeleton']['data']['m_ID'])}
    rest = np.array([n['q']+n['t']+n['s'] for n in model['nodes']], dtype='<f4')
    face = json.loads((NATIVE/'face-sources-v1/native-face-avatar-decoded.json').read_text(encoding='utf-8'))
    face_hashes = {v['boneNameHash'] & 0xffffffff for v in face['data']['basePoseConfig']}
    face_ids = [i for i,n in enumerate(model['nodes']) if zlib.crc32(n['name'].encode()) in face_hashes]
    clips, receipts, failures = [], [], []
    started = time.perf_counter()
    for selected in selections:
        name = selected['source_name']; short = selected['suggested_id']
        try:
            row = next(r for r in rows if r['name'] == name)
            base = Path(row['source_root'])
            raw_clip = base/row['raw']
            assert hashlib.sha256(raw_clip.read_bytes()).hexdigest() == row['sha256'], 'Source object SHA256 mismatch'
            clip = json.loads((base/row['decoded']).read_text(encoding='utf-8'))
            bindings = clip['m_ClipBindingConstant']['genericBindings']
            float_sample = base/'sampled-curves'/(Path(row['acl_buffers']['FloatBufferData']['path']).name+'.samples')
            header = struct.unpack_from('<8sBHIIff', float_sample.read_bytes())
            scalar = [b for b in bindings if b['typeID'] != 4 and not b['isPPtrCurve']]
            assert len(scalar) == header[3], 'Scalar binding mismatch'
            channels = {attributes[b['attribute']]:i for i,b in enumerate(scalar) if b['typeID']==95 and b['customType']==8 and b['attribute'] in attributes}
            channel_path = solved/(short+'.channels.json'); save(channel_path, channels)
            body_path = solved/(short+'.body.json')
            assert not body_path.exists()
            process = subprocess.run(['C:/Program Files/dotnet/dotnet.exe',str(NATIVE/'solver-v2/Probe.dll'),str(ROOT/'MotionConversionResearch-20261019/source-avatar.json'),str(channel_path),str(float_sample),str(body_path)], capture_output=True, text=True)
            assert process.returncode == 0, 'Native body solver failed'
            body = json.loads(body_path.read_text(encoding='utf-8'))
            frames, fps = body['frames'], body['fps']
            rotations = [b for b in bindings if b['typeID']==4 and b['attribute']==2]
            tracks = [b['path'] for b in rotations]
            assert len(tracks)==clip['m_AclCompressedBuffer']['OutputTrackCount'] and len(set(tracks))==len(tracks)
            masks = base64.b64decode(clip['m_AclCompressedBuffer']['TransformSubTrackMasks']['data'])
            group = (len(tracks)+7)//8
            def present(component,index):
                return bool(masks[component*group+index//8] & (1<<(7-index%8)))
            for component,attribute in enumerate([1,2,3]):
                actual = {b['path'] for b in bindings if b['typeID']==4 and b['attribute']==attribute}
                assert {h for i,h in enumerate(tracks) if present(component,i)}==actual, 'Transform mask mismatch'
            transform_sample = base/'sampled-curves'/(Path(row['acl_buffers']['TransformBufferData']['path']).name+'.samples')
            transform_bytes = transform_sample.read_bytes()
            th = struct.unpack_from('<8sBHIIff',transform_bytes)
            assert th[1]==12 and th[3]==len(tracks) and th[4]==frames
            values = np.frombuffer(transform_bytes,dtype='<f4',offset=27).reshape(frames,len(tracks),10)
            native = np.broadcast_to(rest,(frames,*rest.shape)).copy(); unmatched=[]
            for i,path in enumerate(tracks):
                node = hashes.get(path)
                if node is None:
                    unmatched.append(path); continue
                if present(0,i): native[:,node,4:7]=values[:,i,4:7]
                if present(1,i): native[:,node,:4]=values[:,i,:4]
                if present(2,i): native[:,node,7:10]=values[:,i,7:10]
            for i,bone in enumerate(body['bones']): native[:,paths[bone['Path']],:4]=[f['rotations'][i] for f in body['samples']]
            hip = paths[next(b['Path'] for b in body['bones'] if b['Slot']==0)]
            native[:,hip,4:7]=[f['hips'] for f in body['samples']]
            native[:,0,:4]=[f['motionQ'] for f in body['samples']]
            native[:,0,4:7]=[f['motionT'] for f in body['samples']]
            assert np.isfinite(native).all(), 'Non-finite source pose'
            q = native[:,:,:4]; q/=np.maximum(np.linalg.norm(q,axis=-1,keepdims=True),1e-20)
            for f in range(1,frames): q[f,np.sum(q[f-1]*q[f],axis=-1)<0]*=-1
            dest = motions/(short+'.motion')
            with dest.open('xb') as f:
                f.write(struct.pack('<8sIIf',b'ENFMOT1\0',len(rest),frames,fps)); f.write(native.astype('<f4').tobytes())
            moving = np.max(np.abs(native-native[:1]),axis=(0,2))
            info = dict(name=short,source_name=name,label=selected.get('label_zh',name),file=dest.name,frames=frames,fps=fps,duration=(frames-1)/fps,loop=bool(clip['m_MuscleClip']['m_LoopTime']),unmatched_transform_paths=unmatched,moving_face_bones=sum(moving[i]>1e-5 for i in face_ids),source_clip=str(base/row['decoded']))
            clips.append(info)
            receipts.append(dict(selection=selected,source=row,output=info,source_object_sha256_verified=True,native_motion_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),native_body_channels=len(channels),native_body_bones=len(body['bones']),face_note='Source face tracks retained in ENFMOT1; current 58-bone body bake does not replay native 97-bone faces.'))
            print(short,'OK',frames,flush=True)
        except Exception as exc:
            failures.append(dict(source_name=name,error=type(exc).__name__+': '+str(exc)))
            print(short,'FAILED',type(exc).__name__,str(exc),flush=True)
    save(motions/'manifest.json',dict(format='ENFMOT1',notes=['Original source body and face tracks retained. Current runtime uses separately baked target body curves.'],clips=clips,errors=failures))
    save(output/'conversion-receipts.json',dict(elapsed_seconds=time.perf_counter()-started,clips=receipts,errors=failures))
    print('RESULT',len(clips),'passed',len(failures),'failed',flush=True)
    if failures: raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--selection',default=str(PACK/'source-hunt-report.json')); p.add_argument('--inventory',default=str(PACK/'source-candidates.json')); p.add_argument('--output',default=str(PACK/'converted-story'))
    a=p.parse_args(); selection=json.loads(Path(a.selection).read_text(encoding='utf-8')); rows=json.loads(Path(a.inventory).read_text(encoding='utf-8'))
    run(selection['selected_segments'] if isinstance(selection,dict) else selection,rows,Path(a.output))
