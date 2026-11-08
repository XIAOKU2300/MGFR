from pathlib import Path
import shutil

lab=Path(__file__).resolve().parents[1]
project=lab/'Probe2'
assert not project.exists()
source=(lab/'Source/WardrobeProbe.cs').read_text(encoding='utf8').replace('public static class WardrobeProbe','public static class WardrobeProbe2')
source=source.replace('            Action<string,Vector3,Vector3> shot=', '            SkinnedMeshRenderer captureTarget=null;\n            Action<string,Vector3,Vector3> shot=')
source=source.replace('                camera.transform.position=eye;camera.transform.LookAt(aim);camera.Render();', '''                // Editor batch rendering may retain stale GPU skinning. Bake the
                // actual current skinned mesh for each capture instead.
                var snapshot=new Mesh();captureTarget.BakeMesh(snapshot);
                var display=new GameObject("Current baked wardrobe pose");display.transform.SetParent(captureTarget.transform,false);
                display.AddComponent<MeshFilter>().sharedMesh=snapshot;display.AddComponent<MeshRenderer>().sharedMaterials=captureTarget.sharedMaterials;
                bool enabled=captureTarget.enabled;captureTarget.enabled=false;
                camera.transform.position=eye;camera.transform.LookAt(aim);camera.Render();''')
source=source.replace('                NewFile(Path.Combine(output,name+".png"),image.EncodeToPNG());', '''                NewFile(Path.Combine(output,name+".png"),image.EncodeToPNG());
                captureTarget.enabled=enabled;UnityEngine.Object.DestroyImmediate(display);UnityEngine.Object.DestroyImmediate(snapshot);''')
source=source.replace('var renderer=loader.Renderer;var source=renderer.sharedMesh;', 'var renderer=loader.Renderer;captureTarget=renderer;var source=renderer.sharedMesh;')
for p in (lab/'Source/WardrobeProbe2.cs',project/'Assets/Editor/WardrobeProbe2.cs'):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:f.write(source)
for f in (lab/'Probe/Assets/Character').glob('*'):
    if f.is_file() and not f.name.endswith('.meta'):
        dest=project/'Assets/Character'/f.name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(f,dest)
for f in ('ProjectSettings/ProjectVersion.txt','ProjectSettings/ProjectSettings.asset','Packages/manifest.json'):
    dest=project/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lab/'Probe'/f,dest)
with (project/'.gitignore').open('x') as f:f.write('*\n')
print(project)
