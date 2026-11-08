from pathlib import Path
import hashlib,json,os,uuid
root=Path(__file__).resolve().parent
folder=root/'Activation'
plan=json.loads((folder/'plan.json').read_text(encoding='utf-8'))
backups=json.loads((folder/'backup-receipt.json').read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for row in backups:
    if sha(Path(row['backup']))!=row['sha256']:raise RuntimeError('Backup changed')
for row in plan:
    target=Path(row['target']).resolve();staged=Path(row['staged']).resolve()
    if not target.is_relative_to(root.parent) or not staged.is_relative_to(folder):raise ValueError('Target outside declared scope')
    if sha(staged)!=row['newSha256']:raise RuntimeError('Staged file changed')
    if row['oldSha256'] is None:
        if target.exists():raise RuntimeError('New target now exists')
    elif sha(target)!=row['oldSha256']:raise RuntimeError('Active target changed')
for row in plan:
    target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_name(target.name+'.stereo-'+uuid.uuid4().hex+'.tmp')
    with temporary.open('xb') as stream:stream.write(Path(row['staged']).read_bytes())
    os.replace(temporary,target)
    if sha(target)!=row['newSha256']:raise RuntimeError('Activated file hash mismatch')
with (folder/'activation-receipt.json').open('x',encoding='utf-8') as stream:json.dump({'pass':True,'overwritten':len(backups),'created':len(plan)-len(backups),'files':plan,'authorization':'User explicitly requested continuing to completion without confirmation; existing targets backed up and verified'},stream,ensure_ascii=False,indent=2)
print('ACTIVATED_VERIFIED_FILES',len(plan))
