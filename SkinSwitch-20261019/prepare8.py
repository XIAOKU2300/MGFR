from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project7';project=lab/'Project8'
assert not project.exists()
changes={}
p=Path('Assets/MGFR/Skins/Resources/SiSwimsuitCloth.shader');s=(old/p).read_text(encoding='utf-8')
a='half facing : VFACE';assert s.count(a)==1
changes[p]=s.replace(a,'bool facing : SV_IsFrontFace').replace('(facing >= 0 ? 1 : -1)','(facing ? 1 : -1)')
p=Path('Assets/MGFR/Skins/ZmdSkinBinding.cs');s=(old/p).read_text(encoding='utf-8')
a='                            zmd.shader = clothShader;';assert s.count(a)==1
b='''                            int alphaQueue = zmd.renderQueue;
                            zmd.shader = clothShader;
                            zmd.renderQueue = alphaQueue;
                            foreach (string property in new[] { "_Cull", "_SrcBlend", "_DstBlend", "_ZWrite" })
                                Set(zmd, property, appearance.Materials[slot].GetFloat(property));'''
changes[p]=s.replace(a,b)
p=Path('Assets/MGFR/Editor/SkinSwitchBuild8.cs');s=(old/p).read_text(encoding='utf-8')
a='result.summary.result==BuildResult.Succeeded?0:1';assert s.count(a)==1
changes[p]=s.replace(a,'result.summary.result==BuildResult.Succeeded&&result.summary.totalErrors==0?0:1')
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old) in changes]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
 with (project/p).open('x',encoding='utf-8') as f:f.write(s)
print(project)
