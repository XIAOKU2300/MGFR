from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
folder=root/'Activation'
plan=json.loads((folder/'plan.json').read_text(encoding='utf-8'))
snapshot=json.loads((root/'Candidate-v2/source-snapshot.json').read_text(encoding='utf-8'))
for name,expected in snapshot.items():
    path=Path(name).resolve()
    if not path.is_relative_to(root.parent):raise ValueError('Snapshot target outside workspace')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Active source changed after staging: '+str(path))
backups=folder/'Backups';backups.mkdir()
report=[]
for row in plan:
    path=Path(row['target']).resolve()
    if not path.is_relative_to(root.parent):raise ValueError('Target outside workspace')
    if row['oldSha256'] is None:
        if path.exists():raise RuntimeError('New target now exists: '+str(path))
        continue
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=row['oldSha256']:raise RuntimeError('Active target changed: '+str(path))
    target=backups/path.relative_to(root.parent);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(data)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=row['oldSha256']:raise RuntimeError('Backup verification failed')
    report.append({'target':str(path),'backup':str(target),'sha256':row['oldSha256']})
with (folder/'backup-receipt.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
print('VERIFIED_BACKUPS',len(report))
