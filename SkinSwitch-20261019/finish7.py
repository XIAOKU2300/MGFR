from pathlib import Path
lab=Path(__file__).resolve().parent
project=lab/'Project7'
p=project/'Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdCloth.shader'
s=p.read_text(encoding='utf-8')
s=s.replace('Shader "MGFR/ZmdEndfield/Cloth"','Shader "MGFR/ZmdEndfield/SwimsuitCloth"')
anchor=s.index('Name "Outline"');start=s.rfind('        Pass',0,anchor)
brace=s.index('{',start);depth=1;end=brace+1
while depth:
 if s[end]=='{':depth+=1
 elif s[end]=='}':depth-=1
 end+=1
s=s[:start]+s[end:]
s=s.replace('#include "ZmdBuiltInCompat.cginc"','#include "Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdBuiltInCompat.cginc"')
s=s.replace('#include "ZmdCharUtils.cginc"','#include "Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdCharUtils.cginc"')
a='half4 frag (Varyings i) : SV_Target';assert s.count(a)==1
s=s.replace(a,'half4 frag (Varyings i, half facing : VFACE) : SV_Target')
a='half3 normalWS = normalize(i.normalWS);';assert s.count(a)==1
s=s.replace(a,'half3 normalWS = normalize(i.normalWS) * (facing >= 0 ? 1 : -1);')
resources=project/'Assets/MGFR/Skins/Resources';resources.mkdir()
with (resources/'SiSwimsuitCloth.shader').open('x',encoding='utf-8') as f:f.write(s)
s=(lab/'SkinSwitchBuild.cs').read_text(encoding='utf-8').replace('class SkinSwitchBuild','class SkinSwitchBuild8').replace('Build/Windows/MGFR.exe','Build8/Windows/MGFR.exe')
with (project/'Assets/MGFR/Editor/SkinSwitchBuild8.cs').open('x',encoding='utf-8') as f:f.write(s)
print('Added new shader and new Build8 target; existing files overwritten=0')
