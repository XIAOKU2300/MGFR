"""Only run following explicit approval of application-manifest.json."""
from pathlib import Path
import hashlib
import json
import sys
HERE=Path(__file__).resolve().parent
ACTIVE=HERE.parents[1]/'Player/MGFR_Data/StreamingAssets/native-actions'
assert sys.argv[1:]==['--approved-exact-manifest'], 'Explicit reviewed-manifest approval required'
manifest=json.loads((HERE/'application-manifest.json').read_text(encoding='utf-8'))
entries=manifest['entries'];assert len(entries)==166
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'applied-receipt.json').exists()
for item in entries:
    p=Path(item['path']);new=Path(item['candidate']);saved=Path(item['backup'])
    assert p.resolve().is_relative_to(ACTIVE.resolve())
    assert sha(p)==sha(saved)==item['beforeSha256'] and sha(new)==item['afterSha256']
for item in entries:
    with Path(item['path']).open('wb') as stream:stream.write(Path(item['candidate']).read_bytes())
assert all(sha(Path(item['path']))==item['afterSha256'] for item in entries)
with (HERE/'applied-receipt.json').open('x',encoding='utf-8') as f:json.dump({'applied':True,'count':166,'entries':entries},f,ensure_ascii=False,indent=2)
print('Applied 166 reviewed foot-channel updates; other files unchanged.')
