from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

lab=Path(__file__).resolve().parent
main=(lab.parent/'unity-client').resolve()
candidate=lab/'Candidate'
receipt=json.loads((lab/'delivery-receipt.json').read_text(encoding='utf-8'))
assert not (lab/'install-receipt.json').exists()
assert len(receipt['plannedOverwrites'])==5 and len(receipt['newFiles'])==50
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def under_main(path):
    path=Path(path).resolve()
    path.relative_to(main)
    return path

# Check every target, candidate and recovery copy before the first write.
planned=[]
for record in receipt['plannedOverwrites']:
    target=under_main(record['path']);source=candidate/target.relative_to(main)
    assert target.is_file() and sha(target)==record['beforeSha256'], target
    assert sha(Path(record['backup']))==record['beforeSha256']
    assert source.is_file() and sha(source)==record['afterSha256']
    planned.append((target,source,record['afterSha256'],True))
for record in receipt['newFiles']:
    target=under_main(record['path']);source=candidate/target.relative_to(main)
    assert not target.exists(), target
    assert source.is_file() and sha(source)==record['sha256']
    planned.append((target,source,record['sha256'],False))

known={str(p):sha(p) for p in main.rglob('*') if p.is_file() and
       (p.suffix in ('.cs','.shader','.cginc') or p.name=='manifest.json')}
inputs=json.loads((lab/'input-hashes.json').read_text(encoding='utf-8'))
assert all(sha(Path(path))==value for path,value in inputs.items())

for target,source,expected,existing in planned:
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('wb' if existing else 'xb') as stream:stream.write(source.read_bytes())
    assert sha(target)==expected

approved={record['path'] for record in receipt['plannedOverwrites']}
unrelated=[path for path,value in known.items() if path not in approved and sha(Path(path))!=value]
assert not unrelated, unrelated
assert all(sha(Path(path))==value for path,value in inputs.items())
installed={
    'installedAtUtc':datetime.now(timezone.utc).isoformat(),
    'authorization':'User explicitly approved exactly five existing scripts and the listed new files in this chat.',
    'overwrittenCount':5,'newFileCount':50,
    'allInstalledHashesMatchVerifiedCandidate':True,
    'unrelatedExistingSourceFilesChanged':unrelated,
    'inputFilesVerifiedUnchanged':len(inputs),
    'overwrites':receipt['plannedOverwrites'],
    'newFiles':receipt['newFiles'],
    'player':receipt['player'],
    'functionalReport':receipt['functionalReport'],
    'liveReport':receipt['liveReport'],
}
with (lab/'install-receipt.json').open('x',encoding='utf-8') as stream:json.dump(installed,stream,ensure_ascii=False,indent=2)
print('Installed approved scope: 5 existing scripts + 50 new files.')
print('Every installed hash matches the verified candidate. Other existing code and source model hashes are unchanged.')
