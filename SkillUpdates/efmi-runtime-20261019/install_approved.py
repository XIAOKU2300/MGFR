from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

update=Path(__file__).resolve().parent
final=(update/'Final/efmi-mgfr-skin-porting').resolve()
roots=[Path('C:/Users/19829/.codex/skills/efmi-mgfr-skin-porting').resolve(),
       Path('C:/Users/19829/.agents/skills/efmi-mgfr-skin-porting').resolve()]
plan=json.loads((update/'installation-plan-final.json').read_text(encoding='utf-8'))
assert not (update/'installed-receipt.json').exists()
assert len(plan['overwrites'])==2 and len(plan['newFiles'])==20
assert {Path(r['path']).resolve() for r in plan['overwrites']}=={root/'SKILL.md' for root in roots}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def target_root(path):
 for root in roots:
  if path.is_relative_to(root):return root
 raise ValueError('Target escapes the two approved skill folders: '+str(path))

for record in plan['overwrites']:
 target=Path(record['path']).resolve();target_root(target)
 assert sha(target)==record['beforeSha256']
 assert sha(Path(record['backup']))==record['beforeSha256']
 assert sha(final/'SKILL.md')==record['afterSha256']
for record in plan['newFiles']:
 target=Path(record['path']).resolve();root=target_root(target)
 source=Path(record['source']).resolve();source.relative_to(final)
 assert source.relative_to(final)==target.relative_to(root)
 assert not target.exists(),target
 assert sha(source)==record['sha256']

preserved={str(p):sha(p) for root in roots for p in root.rglob('*') if p.is_file() and p.name!='SKILL.md'}
# Install additions before linking them from the two entrypoints.
for record in plan['newFiles']:
 target=Path(record['path']);target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as stream:stream.write(Path(record['source']).read_bytes())
 assert sha(target)==record['sha256']
for record in plan['overwrites']:
 target=Path(record['path'])
 with target.open('wb') as stream:stream.write((final/'SKILL.md').read_bytes())
 assert sha(target)==record['afterSha256']
assert all(sha(Path(p))==value for p,value in preserved.items())
receipt={'installedAtUtc':datetime.now(timezone.utc).isoformat(),
 'authorization':'User explicitly approved both SKILL.md entrypoints and the 20 listed new files.',
 'overwrittenFiles':2,'newFiles':20,'existingOtherFilesChanged':0,
 'roots':[str(root) for root in roots],
 'newFileHashes':{r['path']:r['sha256'] for r in plan['newFiles']},
 'entrypointSha256':sha(final/'SKILL.md')}
with (update/'installed-receipt.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,ensure_ascii=False,indent=2)
print('Merged into both existing efmi-mgfr-skin-porting installations: 2 entrypoints, 20 additions; all other files unchanged.')
