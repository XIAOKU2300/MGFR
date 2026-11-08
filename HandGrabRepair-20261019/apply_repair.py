from pathlib import Path
import hashlib,json
lab=Path(__file__).resolve().parent
root=Path('H:/MGFR/unity-client').resolve()
allowed={
 'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs',
 'Assets/MGFR/Scripts/BareHands/HandGrabCoupling.cs',
}
items=json.loads((lab/'manifest.json').read_text(encoding='utf8'))
assert len(items)==2 and {Path(x['path']).resolve().relative_to(root).as_posix() for x in items}==allowed
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for item in items:
 p=Path(item['path']).resolve();relative=p.relative_to(root)
 assert digest(p)==item['sha256'],f'source changed: {relative}'
 assert digest(lab/'Originals'/relative)==item['sha256'],f'backup mismatch: {relative}'
 assert Path(item['candidate']).read_bytes()==(lab/'Project'/relative).read_bytes(),f'candidate differs from tested code: {relative}'
receipt=[]
for item in items:
 p=Path(item['path'])
 # Both targets are within the six source files explicitly approved by the
 # user in this conversation; this is the regression repair of that change.
 with p.open('wb') as f:f.write(Path(item['candidate']).read_bytes())
 receipt.append({'path':str(p),'sha256':digest(p),'backup':str(lab/'Originals'/p.relative_to(root))})
with (lab/'merge-receipt.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2,ensure_ascii=False)
all_sources=list((root/'Assets/MGFR').rglob('*.cs'))+list((root/'Assets/MGFR').rglob('*.shader'))
differences=[str(p) for p in all_sources if p.read_bytes()!=(lab/'Project'/p.relative_to(root)).read_bytes()]
assert not differences,differences
print(json.dumps({'updated_files':len(receipt),'all_main_code_and_shaders_equal_tested_project':len(all_sources),'backup_verified':True},ensure_ascii=False))
