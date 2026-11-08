from pathlib import Path
import difflib
import hashlib
import json
import shutil

lab = Path('H:/MGFR/HandLab-20261018')
main = Path('H:/MGFR/unity-client')
candidate = lab / 'Project-v4'
relative = Path('Assets/MGFR/Scripts/BareHands/HandJointSource.cs')
backup = lab / 'AlignmentOriginalFiles' / relative
backup.parent.mkdir(parents=True, exist_ok=True)
old = (main / relative).read_bytes()
new = (candidate / relative).read_bytes()
with backup.open('xb') as file:
    file.write(old)
with (lab / 'hand-alignment.patch').open('x', encoding='utf8') as file:
    file.writelines(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True), new.decode('utf-8-sig').splitlines(True), fromfile=str(main / relative), tofile=str(candidate / relative)))
additions = []
for filename in ['HandAlignment.cs', 'HandAlignment.cs.meta']:
    path = Path('Assets/MGFR/Scripts/BareHands') / filename
    assert not (main / path).exists()
    additions.append(dict(source=str(candidate/path), target=str(main/path), sha256=hashlib.sha256((candidate/path).read_bytes()).hexdigest()))
record = dict(target=str(main/relative), source=str(candidate/relative), backup=str(backup), before=hashlib.sha256(old).hexdigest(), after=hashlib.sha256(new).hexdigest(), additions=additions)
with (lab / 'hand-alignment-merge.json').open('x', encoding='utf8') as file:
    json.dump(record, file, ensure_ascii=False, indent=2)
print('Prepared 1 source replacement and 2 new files. Main project unchanged.')
