"""Exact triangle-group wardrobe adaptation. Every destination must be new."""
from pathlib import Path
import sys, json, hashlib, shutil
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/skins'))
from build_swimsuit_v1 import read_base

LAB = Path(__file__).resolve().parents[1]
OUT = LAB / 'Package'
assert not OUT.exists(), 'Choose a new output directory'
OUT.mkdir()

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def emit(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf8') as f: json.dump(data, f, ensure_ascii=False, indent=2)

sources, checks = [], []
specs = [
    ('skirt', 'cover_skirt', '泳装罩裙', 0, [0,-1,0], .12),
    ('sleeves', 'sleeve_left', '左袖片', 1, [1,-.3,0], .10),
    ('sleeves', 'sleeve_right', '右袖片', -1, [-1,-.3,0], .10),
    ('bra_frill', 'chest_frill', '胸前荷叶边', 0, [0,0,-1], .08),
    ('left_wrist', 'wrist_left', '左腕饰', 0, [1,-.2,0], .07),
    ('right_wrist', 'wrist_right', '右腕饰', 0, [-1,-.2,0], .07),
    ('leg_accessory', 'leg_band', '腿饰', 0, [0,-1,0], .08),
    ('sunglasses', 'sunglasses', '墨镜', 0, [0,0,-1], .08),
    ('shoes', 'shoe_left', '左鞋', 1, [0,-.7,-.7], .12),
    ('shoes', 'shoe_right', '右鞋', -1, [0,-.7,-.7], .12),
]

for profile_id, folder in [('barefoot_v4','si-swimsuit-barefoot-ankle-v4'), ('shod_v3','si-swimsuit-ready')]:
    source = ROOT / 'converted/skins' / folder
    model, arrays, morphs = read_base(source)
    pos, normals, uv, bone_ids, weights, indices, binds, sub = arrays
    triangles = indices.reshape(-1,3)
    report = json.loads((source/'conversion-report.json').read_text(encoding='utf8'))
    recorded = {p['part']:p for p in report['parts']}
    dest = OUT / profile_id
    (dest/'parts').mkdir(parents=True)
    (dest/'model').mkdir()
    for f in ('si_model.json','si_model.bin','skin.json','conversion-report.json'):
        shutil.copyfile(source/f, dest/'model'/f)
        sources.append({'path':str(source/f),'sha256':digest(source/f)})
    shutil.copytree(source/'textures',dest/'model/textures')
    sources.extend({'path':str(f),'sha256':digest(f)} for f in sorted((source/'textures').rglob('*')) if f.is_file())
    owned = np.zeros(len(triangles),dtype=bool)
    parts=[]
    for source_name, part_id, label, side, direction, pull in specs:
        if source_name not in recorded: continue
        item = recorded[source_name];lo=item['vertexStart'];hi=lo+item['vertices']
        selected = np.all((triangles>=lo)&(triangles<hi),axis=1)
        if side:
            t=triangles[selected]
            assert np.all(np.min(pos[t,0]*side,axis=1)>0) or source_name in ('sleeves','shoes')
            # Side groups are wholly disjoint; fail on triangles crossing the symmetry plane.
            crossing=selected & (np.min(pos[triangles,0],axis=1)<0) & (np.max(pos[triangles,0],axis=1)>0)
            assert not crossing.any(), f'Cross-side triangle in {source_name}'
            selected &= pos[triangles,0].mean(axis=1)*side>0
        assert selected.any() and not np.any(owned&selected)
        owned |= selected
        tri=triangles[selected];unique=np.unique(tri);points=pos[unique]
        low,high=points.min(0),points.max(0)
        # Use actual surface vertices, never an empty-space box centre.
        target=(low+high)*.5
        if source_name in ('skirt','sleeves','shoes'):
            target[1]=high[1]-.015
        target[2]=low[2]+.02
        candidates=[]
        for x in (float(target[0]),float(low[0]+.25*(high[0]-low[0])),float(high[0]-.25*(high[0]-low[0]))):
            desired=target.copy();desired[0]=x
            vertex=int(unique[np.argmin(np.linalg.norm(points-desired,axis=1))])
            if vertex in [a['vertex'] for a in candidates]: continue
            candidates.append({'vertex':vertex,'position':pos[vertex].tolist(),'normal':normals[vertex].tolist(),
                'boneIndices':bone_ids[vertex].astype(int).tolist(),'boneWeights':weights[vertex].tolist()})
        file=f'parts/{part_id}.indices.bin'
        with (dest/file).open('xb') as f:f.write(tri.astype('<u4').tobytes())
        direction=np.array(direction,float);direction/=np.linalg.norm(direction)
        parts.append({'id':part_id,'label':label,'sourcePart':source_name,'materialSlot':item['material'],
            'indexFile':file,'indexCount':int(tri.size),'triangleCount':len(tri),
            'indexSha256':digest(dest/file),'boundsMin':low.tolist(),'boundsMax':high.tolist(),
            'anchors':candidates,'gripRadiusMetres':.04,'pullDistanceMetres':pull,
            'pullDirectionLocal':direction.tolist(),'snapRadiusMetres':.06,'snapAngleDegrees':35.,
            'interactionIntent':'pinch_then_pull; return_same_part_to_socket',
            'clothOwner':'XPBD' if item['material']==10 else 'skinned',
            'requiresClothOwnershipHandoff':item['material']==10,
            'requiresFootPoseTransition':source_name=='shoes'})
    for source_name in {s[0] for s in specs if s[0] in recorded}:
        item=recorded[source_name];lo=item['vertexStart'];hi=lo+item['vertices']
        expected=np.all((triangles>=lo)&(triangles<hi),axis=1)
        assert np.all(owned[expected]), f'Incomplete split: {source_name}'
        assert expected.sum()==item['triangles']
    profile={'schemaVersion':1,'id':profile_id,'modelDirectory':'model',
        'modelJsonSha256':digest(source/'si_model.json'),'modelBinarySha256':digest(source/'si_model.bin'),
        'vertexCount':len(pos),'boneCount':len(binds),'blendShapeCount':len(morphs),'materialCount':len(sub),
        'indexCount':len(indices),'triangleBufferSha256':hashlib.sha256(indices.astype('<u4').tobytes()).hexdigest(),
        'positionBufferSha256':hashlib.sha256(pos.astype('<f4').tobytes()).hexdigest(),
        'parts':parts,'fixedParts':['body','face','hair','horn','tail','bra','bottom','earrings','hair_ribbon','accessory','tail_accessory'],
        'unsupported':[{'id':'stockings','reason':'No separate stocking geometry or stocking texture-switch contract in this source.'}],
        'footPose':{'id':'flat_barefoot_v4' if profile_id=='barefoot_v4' else 'high_heel_v3',
            'crossProfileEquipAllowed':False,'shoeRemovalRequiresFootPoseSwap':profile_id=='shod_v3',
            'notes':'Do not claim high-heel removal produces a flat-foot pose. Use a host-owned rig/rest/bind transition.'},
        'coveragePolicy':'Swim top and bottom stay on; this adaptation does not build missing underlying body surfaces.',
        'runtimeIntegration':'Explicit adapter API only. No auto-install, hand polling, host mesh writes, cloth changes or launcher changes.'}
    emit(dest/'wardrobe.json',profile)
    checks.append({'profile':profile_id,'parts':len(parts),'removableTriangles':int(owned.sum()),
        'disjoint':True,'allSourceGarmentTrianglesAccounted':True,'positionsUnchanged':True,
        'uvWeightsMorphsRestBindsUnchanged':True,'modelBinaryMatchesSource':digest(source/'si_model.bin')==digest(dest/'model/si_model.bin')})
emit(LAB/'source-hashes.json',sources)
emit(LAB/'structure-checks.json',checks)
print(json.dumps(checks,ensure_ascii=False,indent=2))
