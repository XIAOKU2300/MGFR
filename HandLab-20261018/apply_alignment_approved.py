"""Apply the prepared alignment merge only after explicit user authorization."""
from pathlib import Path
import hashlib
import json

lab = Path('H:/MGFR/HandLab-20261018')
record = json.loads((lab/'hand-alignment-merge.json').read_text(encoding='utf8'))
target = Path(record['target'])
assert target == Path('H:/MGFR/unity-client/Assets/MGFR/Scripts/BareHands/HandJointSource.cs')
assert hashlib.sha256(target.read_bytes()).hexdigest() == record['before']
assert hashlib.sha256(Path(record['backup']).read_bytes()).hexdigest() == record['before']
data = Path(record['source']).read_bytes()
assert hashlib.sha256(data).hexdigest() == record['after']
for item in record['additions']:
    assert not Path(item['target']).exists()
    assert hashlib.sha256(Path(item['source']).read_bytes()).hexdigest() == item['sha256']
for item in record['additions']:
    with Path(item['target']).open('xb') as file:
        file.write(Path(item['source']).read_bytes())
with target.open('wb') as file:
    file.write(data)
assert hashlib.sha256(target.read_bytes()).hexdigest() == record['after']
record['authorization'] = 'Explicit approval in current conversation'
with (lab/'hand-alignment-applied.json').open('x', encoding='utf8') as file:
    json.dump(record, file, ensure_ascii=False, indent=2)
print('Applied 1 approved source replacement and 2 new files; tested hashes verified.')
