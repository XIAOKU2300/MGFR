"""Extend the reviewed math solver to all 61 native body DOFs.
Toe swing axes are checked geometrically in the actual neutral rig.
"""
from pathlib import Path
import json,shutil,numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parent;OLD=Path('H:/MGFR/MotionConversionResearch-20261019/solver-probe-v1');OUT=ROOT/'solver-v2';OUT.mkdir(exist_ok=False)
for source in OLD.glob('*.cs'):
 s=source.read_text(encoding='utf-8')
 if source.name=='AvatarMuscleReferential.cs':
  s=s.replace('["Left Toes Up-Down"] = ((int)BoneType.LeftToes, 1)', '["Left Toes Up-Down"] = ((int)BoneType.LeftToes, 2)').replace('["Right Toes Up-Down"] = ((int)BoneType.RightToes, 1)', '["Right Toes Up-Down"] = ((int)BoneType.RightToes, 2)')
  anchor='        for (int arm = 0; arm < 2; arm++)'
  extra='''        table["Left Foot Twist Roll"] = ((int)BoneType.LeftFoot, 0);
        table["Right Foot Twist Roll"] = ((int)BoneType.RightFoot, 0);
        table["Left Toes Left-Right"] = ((int)BoneType.LeftToes, 1);
        table["Right Toes Left-Right"] = ((int)BoneType.RightToes, 1);
        table["Left Toes Twist Roll"] = ((int)BoneType.LeftToes, 0);
        table["Right Toes Twist Roll"] = ((int)BoneType.RightToes, 0);
'''
  assert anchor in s;s=s.replace(anchor,extra+anchor)
 with (OUT/source.name).open('x',encoding='utf-8') as f:f.write(s)
for name in ['Probe.runtimeconfig.json','native-muscles.json']:
 with (OUT/name).open('xb') as f:f.write((OLD/name).read_bytes())
rsp=(OLD/'compile-v2.rsp').read_text(encoding='utf-8').replace(str(OLD),str(OUT))+'\n-langversion:preview\n'
with (OUT/'compile.rsp').open('x',encoding='utf-8') as f:f.write(rsp)
# Geometry check: the toes point along local twist X. Neutral pre-basis maps
# swing Z to sagittal pitch (world X), swing Y to horizontal yaw (world Y).
a=json.loads(Path('H:/MGFR/MotionConversionResearch-20261019/source-avatar.json').read_text(encoding='utf-8'));h=a['m_Avatar']['m_Human']['data'];sk=h['m_Skeleton']['data'];pose=h['m_SkeletonPose']['data']['m_X'];world=[]
q=lambda p:Rotation.from_quat([p[c] for c in 'xyzw'])
for i,n in enumerate(sk['m_Node']):
 r=q(pose[i]['q']);par=n['m_ParentId'];world.append(world[par]*r if par>=0 else r)
checks=[]
for slot in [20,21]:
 node=h['m_HumanBoneIndex'][slot];parent=sk['m_Node'][node]['m_ParentId'];ax=sk['m_AxesArray'][sk['m_Node'][node]['m_AxesId']];basis=(world[parent]*q(ax['m_PreQ'])).as_matrix()
 assert abs(basis[0,2])>.99 and abs(basis[1,1])>.99 and abs(basis[2,0])>.99
 checks.append({'slot':slot,'world_axes_columns_xyz':basis.tolist(),'up_down_axis':2,'left_right_axis':1,'twist_roll_axis':0})
with (OUT/'native-axis-checks.json').open('x',encoding='utf-8') as f:json.dump({'body_muscle_count':61,'toe_geometry_checks':checks,'scope':'Neutral-rig axis verification, not a native-engine frame equality test.'},f,indent=2)
print(OUT)
