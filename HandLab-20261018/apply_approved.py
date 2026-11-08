"""Execute only after explicit authorization for the two prepared overwrites."""
from pathlib import Path
import json,hashlib,shutil
lab=Path('H:/MGFR/HandLab-20261018')
changes=json.loads((lab/'main-overwrite-manifest.json').read_text(encoding='utf8'))
additions=json.loads((lab/'main-additions-manifest.json').read_text(encoding='utf8'))
for item in changes:
 assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['before'],item['path']
 assert hashlib.sha256(Path(item['backup']).read_bytes()).hexdigest()==item['before']
 assert hashlib.sha256(Path(item['prepared']).read_bytes()).hexdigest()==item['after']
assert all(not Path(item['target']).exists() for item in additions)
for item in additions:
 src,dst=Path(item['source']),Path(item['target']);dst.parent.mkdir(parents=True,exist_ok=True)
 with src.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==item['sha256']
for item in changes:
 target=Path(item['path']);data=Path(item['prepared']).read_bytes()
 with target.open('wb') as f:f.write(data)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==item['after']
with (lab/'main-applied.json').open('x',encoding='utf8') as f:json.dump(dict(authorization='Explicit user approval in this conversation',overwrites=changes,added_files=len(additions)),f,ensure_ascii=False,indent=2)
print('Applied 2 approved configuration replacements and',len(additions),'new files; hashes match the tested build.')
