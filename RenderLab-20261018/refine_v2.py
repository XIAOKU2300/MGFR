from pathlib import Path
import shutil
lab=Path('H:/MGFR/RenderLab-20261018');src=lab/'Sources/v1';dst=lab/'Sources/v2';dst.mkdir(exist_ok=False)
for p in src.iterdir():
 text=p.read_text(encoding='utf8')
 if p.suffix=='.shader':
  text=text.replace('float band=smoothstep(_ShadowThreshold-_Softness,_ShadowThreshold+_Softness,ndl*.5+.5);',
   'float halfLambert=saturate(ndl*.5+.5);\n    float band=lerp(halfLambert,smoothstep(_ShadowThreshold-_Softness,_ShadowThreshold+_Softness,halfLambert),.78);')
  text=text.replace('metal=warm*smoothstep(.035,.24,tex.r);',
   'metal=max(warm*smoothstep(.035,.24,tex.r),smoothstep(.78,.96,packed.r)*_HasPacked*.72);')
  text=text.replace('float front=dot(normalize(_SiHeadForward.xyz),l);',
   'float3 headUp=normalize(_SiHeadUp.xyz);\n     float3 horizontalLight=l-headUp*dot(l,headUp);\n     horizontalLight=normalize(horizontalLight+normalize(_SiHeadForward.xyz)*.0001);\n     float front=dot(normalize(_SiHeadForward.xyz),horizontalLight);')
  text=text.replace('shade=lerp(shade,lerp(_ShadowTint.rgb,_LightTint.rgb,faceLight),mask);',
   'float3 faceShade=lerp(_ShadowTint.rgb,_LightTint.rgb,faceLight);\n     faceShade*=.89+.11*halfLambert;\n     shade=lerp(shade,faceShade,mask);')
  text=text.replace('lerp(1,2.2,metal)','lerp(1,3.0,metal)')
 elif p.name=='SiStylizedRenderer.cs':
  text=text.replace('Shader.Find("MGFR/StylizedCharacter")','Resources.Load<Shader>("MgfrStylized")')
  text=text.replace('m.SetFloat("_MatCapStrength",.13f)','m.SetFloat("_MatCapStrength",.24f)')
  text=text.replace('(.14f,.18f,.2f,.72f)','(.14f,.18f,.2f,.48f)')
  text=text.replace('m.SetFloat("_OutlineWidth",.00065f)','m.SetFloat("_OutlineWidth",.0004f)')
  text=text.replace('m.SetFloat("_Brightness",1.09f)','m.SetFloat("_Brightness",1.15f)')
  text=text.replace('(.87f,.72f,.7f)','(.89f,.78f,.75f)')
  text=text.replace('(.59f,.71f,.72f)','(.68f,.77f,.78f)')
  text=text.replace('m.SetFloat("_OutlineWidth",.00085f)','m.SetFloat("_OutlineWidth",.00035f)')
  text=text.replace('m.SetFloat("_Softness",.10f)','m.SetFloat("_Softness",.14f)')
  text=text.replace('texture.LoadImage(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"stylized",file)),false);','texture.LoadImage(File.ReadAllBytes(Path.Combine(Application.streamingAssetsPath,"stylized",file)),true);')
  text=text.replace('SetStylized(true);IsReady=true;',
   'QualitySettings.antiAliasing=4;Camera.main.allowMSAA=true;\n   SetStylized(true);IsReady=true;')
 elif p.name=='StylizedBuild.cs':
  text=text.replace('public static void Build()', '[MenuItem("MGFR/Build/Stylized Windows Player (Mono)",priority=63)]\n  public static void Build()')
 elif p.name=='RenderReview.cs':
  text=text.replace('camera.targetTexture=rt;','rt.antiAliasing=4;camera.targetTexture=rt;')
 with (dst/p.name).open('x',encoding='utf8') as f:f.write(text)
prep=(lab/'prepare_candidate.py').read_text(encoding='utf8')
prep=prep.replace("if p.suffix=='.shader':dst=project/'Assets/MGFR/Shaders'/p.name", "if p.suffix=='.shader':\n  dst=project/'Assets/MGFR/Resources'/p.name;dst.parent.mkdir(exist_ok=True)")
with (lab/'prepare_candidate_v2.py').open('x',encoding='utf8') as f:f.write(prep)
print('Prepared new v2 source files; v1 preserved')
