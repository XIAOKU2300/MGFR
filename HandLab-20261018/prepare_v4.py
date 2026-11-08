from pathlib import Path
import shutil

lab = Path('H:/MGFR/HandLab-20261018')
source = lab / 'Sources/v4'
original = lab / 'Project-v3/Assets/MGFR/Scripts/BareHands/HandJointSource.cs'
text = original.read_text(encoding='utf8')
text = text.replace('Read(s.leftHand,Frames[0],', 'Read(0,s.leftHand,Frames[0],').replace('Read(s.rightHand,Frames[1],', 'Read(1,s.rightHand,Frames[1],')
text = text.replace('void Read(XRHand hand,HandFrame f,bool updated)', 'void Read(int handIndex,XRHand hand,HandFrame f,bool updated)')
line = 'f.Tracked=f.ValidCount>=20&&f.Valid[0]&&f.Valid[1]&&f.Valid[7]&&f.Valid[12]&&f.Valid[17]&&f.Valid[22];'
assert line in text
text = text.replace(line, line + '\n   if(HandAlignment.Instance!=null)HandAlignment.Instance.Apply(handIndex,f);')
with (source / 'HandJointSource.cs').open('x', encoding='utf8') as file:
    file.write(text)
project = lab / 'Project-v4'

def ignore(path, names):
    return ['HandJointSource.cs'] if Path(path).name == 'BareHands' else []

for folder in ('Assets', 'Packages', 'ProjectSettings'):
    shutil.copytree(lab / 'Project-v3' / folder, project / folder, ignore=ignore)
for item in source.iterdir():
    folder = 'Editor' if item.name == 'HandAlignmentChecks.cs' else 'Scripts/BareHands'
    target = project / 'Assets/MGFR' / folder / item.name
    with item.open('rb') as reader, target.open('xb') as writer:
        shutil.copyfileobj(reader, writer)
print(project)
