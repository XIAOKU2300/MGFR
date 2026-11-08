from pathlib import Path
import shutil

lab=Path(__file__).resolve().parents[1]
project=lab/'ProbeFinal'
assert not project.exists()
s=(lab/'Adapter/WardrobeAdapter.cs').read_text(encoding='utf8')
s=s.replace('        bool disposed;', '        bool disposed; Vector3[] restVertices; BoneWeight[] restWeights; Matrix4x4[] cachedBinds; Transform[] cachedBones;')
s=s.replace('            working=UnityEngine.Object.Instantiate(original);',
    '            restVertices=original.vertices;restWeights=original.boneWeights;cachedBinds=original.bindposes;cachedBones=renderer.bones;\n            working=UnityEngine.Object.Instantiate(original);')
s=s.replace('Vector3 p=original.vertices[a.vertex];', 'Vector3 p=restVertices[a.vertex];')
s=s.replace('var w=original.boneWeights[a.vertex];var bind=original.bindposes;var bones=renderer.bones;',
    'var w=restWeights[a.vertex];var bind=cachedBinds;var bones=cachedBones;')
for p in (lab/'Package/Adapter/WardrobeAdapter.cs',project/'Assets/Character/WardrobeAdapter.cs'):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8') as f:f.write(s)
for f in (lab/'Probe2/Assets/Character').glob('*'):
    if f.is_file() and not f.name.endswith('.meta') and f.name!='WardrobeAdapter.cs':
        dest=project/'Assets/Character'/f.name;shutil.copyfile(f,dest)
for f in ('Assets/Editor/WardrobeProbe2.cs','ProjectSettings/ProjectVersion.txt','ProjectSettings/ProjectSettings.asset','Packages/manifest.json'):
    dest=project/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lab/'Probe2'/f,dest)
with (project/'.gitignore').open('x') as f:f.write('*\n')
print(project)
