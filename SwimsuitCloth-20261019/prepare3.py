from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project2';project=lab/'Project3'
assert not project.exists()
changes={}
p=Path('Assets/MGFR/Skins/ClothPhysics/SwimsuitClothRuntime.cs');s=(old/p).read_text(encoding='utf-8')
s=s.replace('Vector3[] vertices;int[] sourceIds;','Vector3[] vertices;int[] sourceIds;Transform[] cachedBones;Matrix4x4[] cachedBinds;')
s=s.replace('var source=skins.CurrentAppearance.Mesh;','var source=skins.CurrentAppearance.Mesh;\n            cachedBones=skins.Loader.Renderer.bones;cachedBinds=source.bindposes;')
s=s.replace('var bones=skins.Loader.Renderer.bones;var bind=skins.CurrentAppearance.Mesh.bindposes;',
            'var bones=cachedBones;var bind=cachedBinds;')
s=s.replace('body.Clear();var b=skins.Loader.Renderer.bones;', 'body.Clear();var b=cachedBones;')
s=s.replace('if(skins!=null&&skins.IsReady)\n            {','if(skins!=null&&skins.IsReady&&skins.Style!=null&&skins.Loader!=null&&skins.Loader.Renderer!=null)\n            {')
changes[p]=s
p=Path('Assets/MGFR/Skins/ClothPhysics/SwimsuitClothSolver.cs');s=(old/p).read_text(encoding='utf-8')
s=s.replace('var link=links[i];var a=Particles[link.a];var b=Particles[link.b];',
            'var link=links[i];ref var a=ref Particles[link.a];ref var b=ref Particles[link.b];')
s=s.replace('Particles[link.a]=a;Particles[link.b]=b;link.lambda+=dl;links[i]=link;',
            'link.lambda+=dl;links[i]=link;')
a='''                            if(!heldNearby)foreach(var capsule in hands[h])Project(ref p,capsule);'''
b='''                            var capsules=hands[h];
                            if(!heldNearby&&capsules.Count>0&&(p.position-capsules[capsules.Count-1].a).sqrMagnitude<.24f*.24f)
                                foreach(var capsule in capsules)Project(ref p,capsule);'''
assert s.count(a)==1
s=s.replace(a,b);changes[p]=s
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old) in changes]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
 with (project/p).open('x',encoding='utf-8') as f:f.write(s)
print(project)
