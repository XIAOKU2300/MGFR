from pathlib import Path
import hashlib
import json
import shutil

update=Path(__file__).resolve().parent
skill=update/'Candidate/efmi-mgfr-skin-porting'
original=Path('C:/Users/19829/.codex/skills/efmi-mgfr-skin-porting')
mirror=Path('C:/Users/19829/.agents/skills/efmi-mgfr-skin-porting')
runtime=Path('H:/MGFR/SwimsuitCloth-20261019/Project3/Assets/MGFR/Skins/ClothPhysics')
skin=Path('H:/MGFR/converted/skins/si-swimsuit-barefoot-ankle-v4')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def signature(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

assert not (update/'installation-plan.json').exists()
assert (original/'SKILL.md').read_bytes()==(mirror/'SKILL.md').read_bytes()
for source in original.rglob('*'):
 if source.is_file() and source.name!='SKILL.md':
  target=skill/source.relative_to(original);target.parent.mkdir(parents=True,exist_ok=True)
  with target.open('xb') as f:f.write(source.read_bytes())

sources=skill/'scripts/runtime';sources.mkdir()
for name in ['SwimsuitClothSolver.cs','SwimsuitClothRuntime.cs','ClothQuickCheck.cs']:
 with (sources/name).open('xb') as f:f.write((runtime/name).read_bytes())
with (sources/'SwimsuitClothBuild.cs').open('xb') as f:f.write(Path('H:/MGFR/SwimsuitCloth-20261019/Project3/Assets/MGFR/Editor/SwimsuitClothBuild.cs').read_bytes())

data=json.loads((skin/'si_model.json').read_text(encoding='utf-8-sig'))
profile={
 'id':'si-barefoot-ankle-v4-cloth-20261019','skinId':'si-swimsuit-barefoot-ankle-v4',
 'inputHashes':{name:sha(skin/name) for name in ['si_model.json','si_model.bin']},
 'counts':{k:data['counts'][k] for k in ['vertices','indices','bones','materials','blendShapes']},
 'rigSignature':signature([(b['name'],b['parent']) for b in data['bones']]),
 'morphSignature':signature([b['name'] for b in data['blendShapes']]),
 'clothMaterialSlot':10,
 'regions':[
  {'name':'sleeves','vertexStart':57681,'vertices':6712,'split':'sign of rest x','driverBones':[32,58],'pinAboveY':1.205},
  {'name':'bra_frill','vertexStart':64393,'vertices':2710,'driverBones':[15],'pinAboveY':1.235},
  {'name':'skirt','vertexStart':67103,'vertices':6274,'driverBones':[13],'pinAboveY':.875}],
 'gridSpacingMetres':.03,'maxSubsteps':2,'iterations':4,
 'runtimeSources':[p.name for p in sources.glob('*.cs')],
 'validation':'Source templates compiled and short-run checked in the local Project3; no headset or real pinch acceptance.'}
with (skill/'references/si-runtime-profile.json').open('x',encoding='utf-8') as f:json.dump(profile,f,ensure_ascii=False,indent=2)

overwrites=[];new=[]
for label,root in [('codex',original),('agents',mirror)]:
 source=root/'SKILL.md';backup=update/'Originals'/label/'SKILL.md';backup.parent.mkdir(parents=True)
 with backup.open('xb') as f:f.write(source.read_bytes())
 overwrites.append({'path':str(source),'beforeSha256':sha(source),'afterSha256':sha(skill/'SKILL.md'),'backup':str(backup)})
 for source in skill.rglob('*'):
  if not source.is_file() or source.name=='SKILL.md':continue
  target=root/source.relative_to(skill)
  if target.exists():
   assert sha(target)==sha(source),'Existing non-entrypoint differs: '+str(target)
  else:new.append({'source':str(source),'path':str(target),'sha256':sha(source)})
with (update/'installation-plan.json').open('x',encoding='utf-8') as f:
 json.dump({'overwrites':overwrites,'newFiles':new},f,ensure_ascii=False,indent=2)
print('Prepared candidate; overwrite count='+str(len(overwrites))+'; new file count='+str(len(new)))
