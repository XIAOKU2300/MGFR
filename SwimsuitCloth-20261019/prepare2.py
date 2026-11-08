from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project1';project=lab/'Project2'
assert not project.exists()
p=Path('Assets/MGFR/Skins/ClothPhysics/SwimsuitClothSolver.cs')
s=(old/p).read_text(encoding='utf-8')
s=s.replace('const float spacing = .014f;','const float spacing = .030f;')
s=s.replace('readonly List<Link> links = new List<Link>();','readonly List<Link> links = new List<Link>();\n        readonly HashSet<ulong> bendKeys = new HashSet<ulong>();')
s=s.replace('if(other!=opposite&&Particles[other].group==Particles[opposite].group)',
            'if(other!=opposite&&Particles[other].group==Particles[opposite].group&&bendKeys.Add(Key(other,opposite)))')
s=s.replace('Mathf.Clamp(Mathf.CeilToInt(delta*120),1,4);float dt=Mathf.Clamp(delta, .001f,.033f)/steps;',
            'Mathf.Clamp(Mathf.CeilToInt(delta*90),1,2);float dt=Mathf.Clamp(delta, .001f,.0222f)/steps;')
s=s.replace('iteration<6','iteration<4')
a='''var point=capsule.a+axis*t;var normal=p.position-point;float distance=normal.magnitude;
            if(distance>=capsule.radius||distance<1e-7f)return;'''
b='''var point=capsule.a+axis*t;var normal=p.position-point;float squared=normal.sqrMagnitude;
            if(squared>=capsule.radius*capsule.radius||squared<1e-14f)return;
            float distance=Mathf.Sqrt(squared);'''
assert s.count(a)==1
s=s.replace(a,b)
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old)==p]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
with (project/p).open('x',encoding='utf-8') as f:f.write(s)
print(project)
