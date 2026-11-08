"""Create a minimal independent Unity probe project using the target's actual loader."""
from pathlib import Path
import argparse,json,shutil

def main():
    p=argparse.ArgumentParser();p.add_argument('--client',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('Output exists; choose a new project directory')
    source=a.client/'Assets/MGFR';required=[source/'Scripts/Character/SiCharacterLoader.cs',source/'Scripts/Character/SiModelData.cs',source/'Shaders/MgfrCharacter.shader',a.client/'ProjectSettings/ProjectVersion.txt']
    for f in required:
        if not f.is_file():raise ValueError('Missing required project file: '+str(f))
    a.out.mkdir(parents=True,exist_ok=False)
    def copy(src,relative):
        dst=a.out/relative;dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('xb') as f:f.write(src.read_bytes())
    for f in required[:3]:copy(f,Path('Assets/Character')/f.name)
    shutil.copytree(a.client/'ProjectSettings',a.out/'ProjectSettings')
    for name in ('SwimsuitProbe.cs','BarefootProbe.cs'):copy(Path(__file__).parent/'unity'/name,Path('Assets/Editor')/name)
    packages=a.out/'Packages';packages.mkdir()
    with (packages/'manifest.json').open('x',encoding='utf-8') as f:json.dump({'dependencies':{'com.unity.modules.imageconversion':'1.0.0','com.unity.modules.jsonserialize':'1.0.0','com.unity.modules.animation':'1.0.0'}},f)
    print(a.out)

if __name__=='__main__':main()
