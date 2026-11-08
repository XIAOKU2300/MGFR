from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project4';project=lab/'Project5'
assert not project.exists()
p=Path('Assets/MGFR/Skins/ZmdSkinBinding.cs');s=(old/p).read_text(encoding='utf-8')
a='''                            if (slot == 7) continue;
                            // L is source'''
b='''                            if (slot == 7) continue;
                            // The swimsuit contains deliberately double-sided open
                            // sheets. Backface hull outlines cover their front-lit
                            // reverse faces, even at zero extrusion width.
                            zmd.SetShaderPassEnabled("Outline", false);
                            // L is source'''
assert s.count(a)==1
s=s.replace(a,b)
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old)==p]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
with (project/p).open('x',encoding='utf-8') as f:f.write(s)
print(project)
