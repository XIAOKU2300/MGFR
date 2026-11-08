from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project6';project=lab/'Project7'
assert not project.exists()
changes={}
p=Path('Assets/MGFR/Skins/ZmdSkinBinding.cs');s=(old/p).read_text(encoding='utf-8')
a='''                            zmd.SetShaderPassEnabled("Outline", false);'''
b='''                            var clothShader = Resources.Load<Shader>("SiSwimsuitCloth");
                            if (clothShader == null || !clothShader.isSupported) throw new InvalidOperationException("Swimsuit cloth shader missing.");
                            zmd.shader = clothShader;'''
assert s.count(a)==1
changes[p]=s.replace(a,b)
p=Path('Assets/MGFR/Skins/SkinSwitchReview.cs');s=(old/p).read_text(encoding='utf-8')
a='''        Check("swimsuitNormalBinding", material.GetTexture("_NormalMap").name.Contains("swimsuit_cloth_N"));'''
b=a+'''
        report.Add("clothShader="+material.shader.name+"; packed="+material.GetTexture("_MOR").name+"; metallic="+material.GetFloat("_Metallic")+"; aoOffset="+material.GetFloat("_AO_Offset")+"; passes="+material.passCount);
        Check("doubleSidedClothShader",material.shader.name=="MGFR/ZmdEndfield/SwimsuitCloth");'''
assert s.count(a)==1
changes[p]=s.replace(a,b)
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old) in changes]
for folder in ['Assets','ProjectSettings','Packages']:shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
 with (project/p).open('x',encoding='utf-8') as f:f.write(s)

# A dedicated open-sheet cloth shader leaves the original costume shader intact.
p=Path('Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdCloth.shader')
s=(old/p).read_text(encoding='utf-8')
s=s.replace('Shader "MGFR/ZmdEndfield/Cloth"','Shader "MGFR/ZmdEndfield/SwimsuitCloth"')
anchor=s.index('Name "Outline"')
start=s.rfind('        Pass',0,anchor)
brace=s.index('{',start);depth=1;end=brace+1
while depth:
 if s[end]=='{':depth+=1
 elif s[end]=='}':depth-=1
 end+=1
s=s[:start]+s[end:]
s=s.replace('#include "ZmdBuiltInCompat.cginc"','#include "Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdBuiltInCompat.cginc"')
s=s.replace('#include "ZmdCharUtils.cginc"','#include "Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdCharUtils.cginc"')
a='half4 frag(Varyings i) : SV_Target';assert s.count(a)==1
s=s.replace(a,'half4 frag(Varyings i, half facing : VFACE) : SV_Target')
a='half3 normalWS = normalize(i.normalWS);';assert s.count(a)==1
s=s.replace(a,'half3 normalWS = normalize(i.normalWS) * (facing >= 0 ? 1 : -1);')
resources=project/'Assets/MGFR/Skins/Resources';resources.mkdir()
with (resources/'SiSwimsuitCloth.shader').open('x',encoding='utf-8') as f:f.write(s)
print(project)
