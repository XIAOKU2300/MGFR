from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project3';project=lab/'Project4'
assert not project.exists()
changes={}
p=Path('Assets/MGFR/Scripts/Character/SiCharacterLoader.cs');s=(old/p).read_text(encoding='utf-8')
a='        Color[] _materialBaseDiffuse;';assert s.count(a)==1
s=s.replace(a,'        Material[] _builtMaterials;\n'+a)
a='                AttachRenderer(mesh);';assert s.count(a)==1
s=s.replace(a,a+'\n                _builtMaterials = (Material[])Materials.Clone();')
a='Materials = (Material[])(materials ?? Materials).Clone()';assert s.count(a)==1
s=s.replace(a,'Materials = (Material[])(materials ?? _builtMaterials ?? Materials).Clone()')
changes[p]=s
p=Path('Assets/MGFR/Skins/ZmdSkinBinding.cs');s=(old/p).read_text(encoding='utf-8')
a='Loader.CaptureAppearance("original", previousMesh, PreviousMaterials)';assert s.count(a)==1
changes[p]=s.replace(a,'Loader.CaptureAppearance("original", previousMesh)')
p=Path('Assets/MGFR/RenderStyles/ZmdEndfield/ZmdRenderStyle.cs');s=(old/p).read_text(encoding='utf-8')
a='if(Active)UpdateGlobals();';assert s.count(a)==1
s=s.replace(a,'if(Active||SkinSwitchingEnabled)UpdateGlobals();')
a='Has("-mgfr-zmd")||Has("-mgfr-zmd-review")';assert s.count(a)==1
s=s.replace(a,a+'||Has("-mgfr-skins")')
changes[p]=s
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old) in changes]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
 with (project/p).open('x',encoding='utf-8') as f:f.write(s)
print(project)
