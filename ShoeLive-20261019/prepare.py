from pathlib import Path
import json,shutil,hashlib

lab=Path(__file__).resolve().parent;base=lab.parent/'WardrobeLive-20261019/Project';project=lab/'Project';assert not project.exists()
changes={}
def edit(p,old,new):
    p=Path(p);s=changes.get(p,(base/p).read_text(encoding='utf8'));assert s.count(old)==1,(str(p),old[:70],s.count(old));changes[p]=s.replace(old,new)
skin='Assets/MGFR/Skins/SiSkinSwitcher.cs'
edit(skin,'"si-swimsuit-barefoot-ankle-v4"','"si-swimsuit-shoes"')
edit(skin,'            var previous = CurrentAppearance;', '            MGFR.Wardrobe.ShoeFootPose.Instance?.UndoLift();\n            var previous = CurrentAppearance;')
edit(skin,'            for (int i = 0; i < blend.Length; i++) Loader.Renderer.SetBlendShapeWeight(i, blend[i]);',
 '            for (int i = 0; i < Mathf.Min(blend.Length,Loader.Renderer.sharedMesh.blendShapeCount); i++) Loader.Renderer.SetBlendShapeWeight(i, blend[i]);')
edit(skin,'蓝白泳装 · 赤脚 v4','蓝白泳装 · 左右鞋穿脱')
binding='Assets/MGFR/Skins/ZmdSkinBinding.cs'
edit(binding,'        static string SafeSkinPath(','''        public void VisitShoeMeshes(Action<Mesh> visitor)
        {
            foreach(var v in skinVariants.Values){visitor(v.rawMesh);visitor(v.outlinedMesh);}
        }
        static string SafeSkinPath(''')
idle='Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs'
edit(idle,'        public void Apply(float seconds,float frameDelta=-1)\n        {',
 '        public void Apply(float seconds,float frameDelta=-1)\n        {\n            MGFR.Wardrobe.ShoeFootPose.Instance?.UndoLift();')
leg='Assets/MGFR/Scripts/Experience/LegPlantSolver.cs'
edit(leg,'        void LateUpdate()\n        {','        void LateUpdate(){SolveNow();}\n        public void SolveNow()\n        {')
edit(leg,'            Vector3 goal=bones[target].position-hip.position;', '''            var shoes=MGFR.Wardrobe.ShoeFootPose.Instance;
            bool shoePose=shoes!=null&&shoes.Ready;
            Vector3 lift=shoePose?shoes.transform.up*(shoes.Height*shoes.Weights[h==21?0:1]*scale):Vector3.zero;
            Vector3 goal=bones[target].position+lift-hip.position;''')
edit(leg,'            ankle.rotation=Quaternion.FromToRotation(bones[toe].position-ankle.position,bones[toeTarget].position-ankle.position)*ankle.rotation;',
 '''            if(shoePose){ankle.rotation=bones[0].root.rotation;bones[toe].localRotation=Quaternion.identity;}
            else ankle.rotation=Quaternion.FromToRotation(bones[toe].position-ankle.position,bones[toeTarget].position-ankle.position)*ankle.rotation;''')
edit(leg,'            bones[744].localRotation=bones[23].localRotation;', '''            bones[744].localRotation=bones[23].localRotation;
            var shoes=MGFR.Wardrobe.ShoeFootPose.Instance;
            if(shoes!=null&&shoes.Ready){bones[745].localRotation=bones[24].localRotation;bones[741].localRotation=bones[28].localRotation;}''')
edit(leg,'Vector3.Distance(ankle.position,bones[target].position)', 'Vector3.Distance(ankle.position,bones[target].position+lift)')
cloth='Assets/MGFR/Skins/ClothPhysics/SwimsuitClothRuntime.cs'
edit(cloth,'source.vertexCount!=73377','source.vertexCount!=76308')
edit(cloth,'Swimsuit cloth profile requires barefoot ankle v4 mesh.','Swimsuit cloth profile requires v4 with appended shoes.')
wardrobe='Assets/MGFR/Wardrobe/WardrobeLiveRuntime.cs'
edit(wardrobe,'            if(!cloth.IsReady)return;', '            if(!cloth.IsReady||ShoeFootPose.Instance==null||!ShoeFootPose.Instance.Ready)return;')
edit(wardrobe,'wardrobe/barefoot_v4','wardrobe/with_shoes')
edit(wardrobe,'                adapter.SimulatedClothActive=true;adapter.ClothOwner=this;',
 '                adapter.SimulatedClothActive=true;adapter.ClothOwner=this;adapter.FootPoseOwner=ShoeFootPose.Instance;')
edit(wardrobe,'Ready: 8 parts','Ready: 10 parts including independent shoes')
review='Assets/MGFR/Wardrobe/WardrobeLiveReview.cs'
edit(review,'if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-wardrobe-review")>=0)',
 'if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-wardrobe-review")>=0&&Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-shoe-review")<0)')
def ignore(directory,names):return[n for n in names if (Path(directory)/n).relative_to(base) in changes]
for folder in ('Assets','ProjectSettings','Packages'):shutil.copytree(base/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf8') as f:f.write(s)
for file in ('ShoeFootPose.cs','ShoeReview.cs'):
    p=project/'Assets/MGFR/Wardrobe'/file
    with p.open('xb') as f:f.write((lab/'Source'/file).read_bytes())
shutil.copytree(lab/'Skin',project/'Assets/StreamingAssets/skins/si-swimsuit-shoes')
shutil.copytree(lab/'Profile',project/'Assets/StreamingAssets/wardrobe/with_shoes')
cache=base/'Library/PackageCache'
if cache.exists():shutil.copytree(cache,project/'Library/PackageCache')
with (lab/'source-hashes.json').open('x',encoding='utf8') as f:
    json.dump({str(base/p):hashlib.sha256((base/p).read_bytes()).hexdigest() for p in changes},f,indent=2)
print(project)
