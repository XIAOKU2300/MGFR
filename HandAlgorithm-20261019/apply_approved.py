from pathlib import Path
import hashlib,json,uuid
lab=Path(__file__).resolve().parent
root=Path('H:/MGFR/unity-client').resolve()
items=json.loads((lab/'manifest.json').read_text(encoding='utf8'))
approved={
 'Assets/MGFR/Resources/HandDepth.shader',
 'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs',
 'Assets/MGFR/Scripts/BareHands/HandDepthMesh.cs',
 'Assets/MGFR/Scripts/BareHands/HandGrabCoupling.cs',
 'Assets/MGFR/Scripts/BareHands/HandJointSource.cs',
 'Assets/MGFR/Scripts/BareHands/HandPoseStabilizer.cs',
}
additions={f'Assets/MGFR/Scripts/BareHands/{name}.cs' for name in ('HandOcclusionEnvelope','HandPinchState','HandSurfaceQuery')}
assert len(items)==9
assert {Path(i['target']).resolve().relative_to(root).as_posix() for i in items if i['exists']}==approved
assert {Path(i['target']).resolve().relative_to(root).as_posix() for i in items if not i['exists']}==additions
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for item in items:
 target=Path(item['target']).resolve();relative=target.relative_to(root)
 candidate=Path(item['candidate'])
 built=lab/'Project2'/relative
 assert digest(candidate)==digest(built),f'candidate differs from tested build: {relative}'
 if item['exists']:
  assert digest(target)==item['sha256'],f'source changed: {relative}'
  assert digest(lab/'Originals'/relative)==item['sha256'],f'backup mismatch: {relative}'
 else:
  assert not target.exists() and not target.with_suffix('.cs.meta').exists()
receipt=[]
for item in items:
 target=Path(item['target']);content=Path(item['candidate']).read_bytes()
 with target.open('wb' if item['exists'] else 'xb') as f:f.write(content)
 if not item['exists']:
  with target.with_suffix('.cs.meta').open('x',encoding='utf8') as f:
   f.write('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\n')
 receipt.append({'path':str(target),'sha256':digest(target),'action':'approved overwrite' if item['exists'] else 'add'})
with (lab/'merge-receipt.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2,ensure_ascii=False)
print(json.dumps({'overwritten':len(approved),'new_algorithms':len(additions),'byte_identical_to_tested_build':True,'receipt':str(lab/'merge-receipt.json')},ensure_ascii=False))
