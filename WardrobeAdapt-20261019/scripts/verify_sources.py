from pathlib import Path
import hashlib,json
lab=Path(__file__).resolve().parents[1]
entries=json.loads((lab/'source-hashes.json').read_text(encoding='utf8'))
checks=[{'path':e['path'],'unchanged':hashlib.sha256(Path(e['path']).read_bytes()).hexdigest()==e['sha256']} for e in entries]
report={'filesChecked':len(checks),'allUnchanged':all(e['unchanged'] for e in checks),'files':checks}
with (lab/'source-verification.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2,ensure_ascii=False)
assert report['allUnchanged']
print('all source files unchanged:',len(checks))
