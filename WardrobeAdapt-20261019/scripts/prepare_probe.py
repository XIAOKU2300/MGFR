from pathlib import Path
import shutil,json

lab=Path(__file__).resolve().parents[1]
root=lab.parent
project=lab/'Probe'
assert not project.exists()
files={
    root/'unity-client/Assets/MGFR/Scripts/Character/SiCharacterLoader.cs':'Assets/Character/SiCharacterLoader.cs',
    root/'unity-client/Assets/MGFR/Scripts/Character/SiModelData.cs':'Assets/Character/SiModelData.cs',
    root/'unity-client/Assets/MGFR/Skins/SiAppearance.cs':'Assets/Character/SiAppearance.cs',
    root/'unity-client/Assets/MGFR/Shaders/MgfrCharacter.shader':'Assets/Character/MgfrCharacter.shader',
    root/'unity-client/ProjectSettings/ProjectVersion.txt':'ProjectSettings/ProjectVersion.txt',
    root/'unity-client/ProjectSettings/ProjectSettings.asset':'ProjectSettings/ProjectSettings.asset',
    lab/'Source/WardrobeProbe.cs':'Assets/Editor/WardrobeProbe.cs',
}
for source,relative in files.items():
    dest=project/relative;dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:f.write(source.read_bytes())
# New revision fixes the shoe-only callback and uses runtime-safe destruction.
source=(lab/'Source/WardrobeAdapter.cs').read_text(encoding='utf8')
source=source.replace('FootPoseOwner?.ShoeStateChanged(id,false);Changed?.Invoke(id,false);',
    'if(part.requiresFootPoseTransition)FootPoseOwner?.ShoeStateChanged(id,false);Changed?.Invoke(id,false);')
source=source.replace('UnityEngine.Object.DestroyImmediate(', 'ReleaseObject(')
needle='        public void Dispose()'
source=source.replace(needle,'''        static void ReleaseObject(UnityEngine.Object obj)
        {
            if(obj==null)return;
            if(Application.isPlaying)UnityEngine.Object.Destroy(obj);else UnityEngine.Object.DestroyImmediate(obj);
        }
'''+needle)
for dest in (lab/'Adapter/WardrobeAdapter.cs',project/'Assets/Character/WardrobeAdapter.cs'):
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf8') as f:f.write(source)
(project/'Packages').mkdir()
with (project/'Packages/manifest.json').open('x') as f:
    json.dump({'dependencies':{f'com.unity.modules.{n}':'1.0.0' for n in ('animation','imageconversion','jsonserialize')}},f)
print(project)
