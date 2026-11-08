from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project5';project=lab/'Project6'
assert not project.exists()
changes={}
p=Path('Assets/MGFR/Scripts/Character/SiCharacterLoader.cs');s=(old/p).read_text(encoding='utf-8')
a='            Renderer.sharedMesh = appearance.Mesh; Renderer.sharedMaterials = Materials;';assert s.count(a)==1
s=s.replace(a,'            ReplaceSkinMesh(appearance.Mesh); Renderer.sharedMaterials = Materials;')
a='        public void ApplyAppearance(SiAppearance appearance)';assert s.count(a)==1
b='''        public void ReplaceSkinMesh(Mesh mesh)
        {
            if (Renderer.sharedMesh == mesh) return;
            var current = Renderer.sharedMesh;
            int count = current != null ? current.blendShapeCount : 0;
            var weights = new float[count];
            for (int i = 0; i < count; i++) weights[i] = Renderer.GetBlendShapeWeight(i);
            // Invalidate GPU skinning buffers when vertex count/layout changes.
            // No skinned motion vectors are consumed by this MR forward renderer.
            Renderer.sharedMesh = null;
            Renderer.skinnedMotionVectors = false;
            Renderer.sharedMesh = mesh;
            for (int i = 0; i < Mathf.Min(count, mesh.blendShapeCount); i++) Renderer.SetBlendShapeWeight(i, weights[i]);
        }

'''+a
s=s.replace(a,b);changes[p]=s
p=Path('Assets/MGFR/RenderStyles/ZmdEndfield/ZmdRenderStyle.cs');s=(old/p).read_text(encoding='utf-8')
a='Loader.Renderer.sharedMesh=value?zmdMesh:previousMesh;';assert s.count(a)==1
changes[p]=s.replace(a,'Loader.ReplaceSkinMesh(value?zmdMesh:previousMesh);')
p=Path('Assets/MGFR/Skins/SkinSwitchReview.cs');s=(old/p).read_text(encoding='utf-8')
a='            Check("select_" + id, skins.TrySelect(id));';assert s.count(a)==1
s=s.replace(a,a+'\n            yield return null;')
a='        Check("originalSkinRestored", skins.TrySelect("original"));';assert s.count(a)==1
s=s.replace(a,a+'\n        yield return null;')
changes[p]=s
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old) in changes]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
 with (project/p).open('x',encoding='utf-8') as f:f.write(s)
print(project)
