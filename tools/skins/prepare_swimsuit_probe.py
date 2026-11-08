"""Creates a new minimal Unity project. Never modifies the working Unity client."""
from pathlib import Path
import argparse,json

p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();root=a.output
root.mkdir(parents=True,exist_ok=False)
def write(path,data):
    path=root/path;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data)
source=Path(r'H:\MGFR\unity-client\Assets\MGFR')
for name in ('SiModelData.cs','SiCharacterLoader.cs'):
    write(Path('Assets/Character')/name,(source/'Scripts/Character'/name).read_bytes())
write(Path('Assets/Character/MgfrCharacter.shader'),(source/'Shaders/MgfrCharacter.shader').read_bytes())
write(Path('Assets/Editor/SwimsuitProbe.cs'),Path(__file__).with_name('SwimsuitProbe.cs').read_bytes())
write(Path('Packages/manifest.json'),json.dumps({'dependencies':{'com.unity.modules.imageconversion':'1.0.0','com.unity.modules.jsonserialize':'1.0.0','com.unity.modules.animation':'1.0.0'}}).encode())
write(Path('ProjectSettings/ProjectVersion.txt'),b'm_EditorVersion: 6000.3.26f1\n')
print(root)
