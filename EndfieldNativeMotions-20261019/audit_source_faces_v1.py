"""Independently compare selected exported facial channels to decoded source tracks."""
from pathlib import Path
import base64
import json
import struct
import zlib
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / 'SiMotions-20261019'
model = json.loads((ROOT / 'assets-v1/native-model.json').read_text(encoding='utf-8'))
avatar = json.loads((ROOT.parent / 'MotionConversionResearch-20261019/source-avatar.json').read_text(encoding='utf-8'))
face = json.loads((ROOT / 'face-sources-v1/native-face-avatar-decoded.json').read_text(encoding='utf-8'))
hashes = {v['boneNameHash'] & 0xffffffff for v in face['data']['basePoseConfig']}
face_indices = {i for i, n in enumerate(model['nodes']) if zlib.crc32(n['name'].encode()) in hashes}
assert len(face_indices) == 97
path_indices = {h: i for i, h in enumerate(avatar['m_Avatar']['m_AvatarSkeleton']['data']['m_ID'])}
manifest = json.loads((ROOT / 'motions-v5/manifest.json').read_text(encoding='utf-8'))
rows = []
for base, filename in [(DATA, 'reports/clips.json'), (DATA / 'controller-linked', 'clips.json')]:
    rows.extend((base, row) for row in json.loads((base / filename).read_text(encoding='utf-8')))
results = []
for entry in manifest['clips'][:16]:
    base, row = next((b, r) for b, r in rows if r['name'] == entry['name'])
    clip = json.loads((base / row['decoded']).read_text(encoding='utf-8'))
    paths = [b['path'] for b in clip['m_ClipBindingConstant']['genericBindings'] if b['typeID'] == 4 and b['attribute'] == 2]
    raw = (base / 'sampled-curves' / (Path(row['acl_buffers']['TransformBufferData']['path']).name + '.samples')).read_bytes()
    header = struct.unpack_from('<8sBHIIff', raw)
    values = np.frombuffer(raw, dtype='<f4', offset=27).reshape(header[4], len(paths), 10)
    actual = np.frombuffer((ROOT / 'motions-v5' / entry['file']).read_bytes(), dtype='<f4', offset=20).reshape(entry['frames'], 596, 10)
    masks = base64.b64decode(clip['m_AclCompressedBuffer']['TransformSubTrackMasks']['data'])
    stride = (len(paths) + 7) // 8
    checked = 0
    max_error = 0.0
    for track, path in enumerate(paths):
        node = path_indices.get(path)
        if node not in face_indices:
            continue
        for group, section in [(0, slice(4, 7)), (1, slice(0, 4)), (2, slice(7, 10))]:
            if not masks[group * stride + track // 8] & (1 << (7 - track % 8)):
                continue
            source = values[:, track, section].copy()
            target = actual[:, node, section]
            if group == 1:
                source /= np.linalg.norm(source, axis=1, keepdims=True)
                source[np.sum(source * target, axis=1) < 0] *= -1
            error = float(np.max(np.abs(source - target)))
            max_error = max(max_error, error)
            assert error < 1e-6, (entry['name'], model['nodes'][node]['name'], group, error)
            checked += 1
    movement = np.max(np.abs(actual - actual[:1]), axis=(0, 2))
    moving = [model['nodes'][i]['name'] for i in sorted(face_indices) if movement[i] > 1e-5]
    results.append({'name': entry['name'], 'label': entry['label'], 'source_facial_component_tracks_checked': checked, 'maximum_difference': max_error, 'moving_face_bones': len(moving), 'moving_face_bone_names': moving})
report = {'scope': 'Original decoded TransformBuffer facial channels versus delivered motions-v5, all 16 body clips. Does not prove external runtime emotion dispatch completeness.', 'result': 'PASS: no source facial transform component lost', 'clips': results}
with (ROOT / 'source-face-audit-v1.json').open('x', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
for item in results:
    print(item['label'], 'source components', item['source_facial_component_tracks_checked'], 'moving bones', item['moving_face_bones'], 'max error', item['maximum_difference'])
