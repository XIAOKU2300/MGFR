from pathlib import Path
import re,shutil,hashlib,json
lab=Path(__file__).resolve().parent
root=Path('H:/MGFR/unity-client')
source=Path('H:/MGFR/ZMD')
module=Path('Assets/MGFR/RenderStyles/ZmdEndfield')
candidate=lab/'Candidate'
project=lab/'Project1'
assert not project.exists() and not candidate.exists()
resources=candidate/module/'Resources/ZmdEndfield'
resources.mkdir(parents=True)
study=[]
def write(path,text):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf8',newline='\n') as f:f.write(text)
def reference(p):
 study.append({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
def stereo(s):
 # Every pass keeps single-pass instanced stereo setup, including shadows and outline.
 s=re.sub(r'(struct\s+\w*Attributes\s*\{)',r'\1\n UNITY_VERTEX_INPUT_INSTANCE_ID',s)
 s=re.sub(r'(struct\s+\w*Varyings\s*\{)',r'\1\n UNITY_VERTEX_OUTPUT_STEREO',s)
 functions=list(re.finditer(r'(\w*Varyings)\s+(\w+)\s*\(\s*\w*Attributes\s+(\w+)\s*\)\s*\{',s))
 for match in reversed(functions):
  start=match.end();end=s.index('return ',start)
  segment=s[start:end]
  decl=re.search(r'\b'+match.group(1)+r'\s+(\w+)\s*;',segment)
  if decl:
   out=decl.group(1);pos=start+decl.end()
   s=s[:pos]+f'\n UNITY_SETUP_INSTANCE_ID({match.group(3)}); UNITY_INITIALIZE_OUTPUT({match.group(1)},{out}); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO({out});'+s[pos:]
 s=re.sub(r'(half4\s+(?:frag|SChar_OutlineFrag|SChar_ShadowFrag)\s*\(\s*\w*Varyings\s+(\w+)\s*\)\s*:\s*SV_\w+\s*\{)',lambda m:m[1]+'\n UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX('+m[2]+');',s,flags=re.I)
 return s

compat=(lab/'Source/ZmdBuiltInCompat.cginc').read_text(encoding='utf8')
write(resources/'ZmdBuiltInCompat.cginc',compat)
p=source/'Packages/com.zmd.shaderlibrary/S_Char_Utils.hlsl';reference(p)
s=p.read_text(encoding='utf8-sig')
s=re.sub(r'#include "Packages/com\.unity[^\n]+','',s)
s=s.replace('#define S_CHAR_UTILS_INCLUDED','#define S_CHAR_UTILS_INCLUDED\n#include "ZmdBuiltInCompat.cginc"')
a=s.index('half3 SamplePerObjectScreenSpaceShadowmap(');b=s.index('// =======================================================================',a)
s=s[:a]+'''half3 SamplePerObjectScreenSpaceShadowmap(float4 shadowCoord)
{return ZmdScreenShadow(shadowCoord).xxx;}
'''+s[b:]
s=s.replace('TEXTURE2D_X_FLOAT(_PerObjectTransparentDepthTexture);','// Transparent hair uses the shared depth attachment in this port.\n#define _PerObjectTransparentDepthTexture _CameraDepthTexture')
s=s.replace('float3 smoothNormalWS = VNI.tangentWS * v.uv7.x + VNI.bitangentWS * v.uv7.y + VNI.normalWS * v.uv7.z;','float3 smoothNormalWS = VNI.tangentWS * v.uv7.x + VNI.bitangentWS * v.uv7.y + VNI.normalWS * v.uv7.z;\n    if(dot(smoothNormalWS,smoothNormalWS)<.1)smoothNormalWS=VNI.normalWS;')
a=s.index('    float4 positionCS = TransformWorldToHClip(ApplyShadowBias(');b=s.index('    o.positionCS = positionCS;',a)
s=s[:a]+'''    float4 positionCS=UnityClipSpaceShadowCasterPos(v.positionOS.xyz,v.normalOS);
    positionCS=UnityApplyLinearShadowBias(positionCS);
'''+s[b:]
s=s.replace('clip(0.5 - _PerObjectShadowEnabled);','// Standard Built-in shadow caster replaces the URP projector feature.')
write(resources/'ZmdCharUtils.cginc',stereo(s))

for kind in ('Face','Skin','Cloth','Hair'):
 p=source/f'Assets/Char/Shader/S_Char_{kind}.shader';reference(p)
 s=p.read_text(encoding='utf8-sig').replace(f'ZMD/S_Char_{kind}',f'MGFR/ZmdEndfield/{kind}')
 s=s.replace('"RenderPipeline"="UniversalPipeline"','').replace('"RenderPipeline" = "UniversalPipeline"','')
 s=re.sub(r'#include "Packages/com\.unity[^\n]+','#include "ZmdBuiltInCompat.cginc"',s)
 s=s.replace('Packages/com.zmd.shaderlibrary/S_Char_Utils.hlsl','ZmdCharUtils.cginc')
 s=re.sub(r'#pragma multi_compile _ _MAIN_LIGHT_SHADOWS(?:_CASCADE)?','',s)
 s=s.replace('#pragma multi_compile _ _SHADOWS_SOFT','#pragma multi_compile_fwdbase')
 s=s.replace('HLSLPROGRAM','HLSLPROGRAM\n#pragma target 3.5\n#pragma multi_compile_instancing')
 s=s.replace('"UniversalForwardOnly"','"ForwardBase"').replace('"UniversalForward"','"ForwardBase"')
 # Drop URP-only depth passes. Built-in derives its depth via ShadowCaster.
 s=re.sub(r'\n        Pass\s*\{\s*Name "DepthOnly".*?ENDHLSL\s*\}', '',s,flags=re.S)
 if kind=='Hair':
  s=re.sub(r'\n        Pass\s*\{\s*Name "Hair_Transparency".*?ENDHLSL\s*\}', '',s,flags=re.S)
 # Source-specific equations are retained; adapt per-material render state.
 s=s.replace('    Properties\n    {','''    Properties
    {
        _ZmdExposure("Character exposure",Float)=1
        _ZmdNormalScale("Raw RG normal scale",Float)=1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull",Float)=0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend("Source blend",Float)=1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend("Destination blend",Float)=0
        [Enum(Off,0,On,1)] _ZWrite("Depth write",Float)=1''')
 if kind!='Hair':
  s=s.replace('_ZmdExposure("Character exposure",Float)=1','_Color("Model material tint",Color)=(1,1,1,1)\n        _ZmdExposure("Character exposure",Float)=1')
  s=s.replace('half4 _BaseColor_ST;', 'half4 _BaseColor_ST;\n                half4 _Color;')
  s=s.replace('half4 baseMap = SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, i.uv);','half4 baseMap = SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, i.uv)*_Color;')
  s=s.replace('SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, uv) * _TintColor','SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, uv) * _TintColor * _Color')
 if kind=='Face':
  # Lip / mask textures are shared game resources; keep complete face mode.
  pass
 if kind=='Cloth':
  s=s.replace('half4 MOR = SAMPLE_TEXTURE2D(_MOR, sampler_MOR, uv);','half4 MOR = SAMPLE_TEXTURE2D(_MOR, sampler_MOR, uv);\n                MOR.a=1-MOR.a; // Si P alpha is smoothness; ZMD MOR alpha is roughness.')
  s=s.replace('UnpackNormal(normalMap)','ZmdUnpackRG(normalMap)')
  s=s.replace('return half4(finalColor , 1.0);','return half4(ZmdFinish(finalColor),alpha);')
 if kind=='Skin':s=s.replace('UnpackNormal(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, i.uv))','ZmdUnpackRG(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, i.uv))')
 if kind=='Hair':
  s=s.replace('normalTS_HL.xy = normal.ba * 2.0 - 1.0;','normalTS_HL.xy = (normal.ba * 2.0 - 1.0)*half2(1,-1);')
  s=s.replace('(normal.rg * 2.0 - 1.0) * _NormalStrength','(normal.rg * 2.0 - 1.0) * half2(1,-1) * _NormalStrength')
 s=s.replace('return half4(finalColor, 1.0);','return half4(ZmdFinish(finalColor), 1.0);').replace('return half4(finalColor, alpha);','return half4(ZmdFinish(finalColor), alpha);')
 # States are scoped to the forward pass, not shadow / outline passes.
 pos=s.index('Name "ForwardLit"') if 'Name "ForwardLit"' in s else s.index('Name "ForwardBase"')
 end=s.index('HLSLPROGRAM',pos)
 segment=s[pos:end]
 segment=re.sub(r'\s+(?:Blend [^\n]+|ZWrite (?:On|Off)|Cull (?:Back|Front|Off))','',segment)
 segment+='\n            Cull [_Cull] ZWrite [_ZWrite] Blend [_SrcBlend] [_DstBlend]\n            '
 s=s[:pos]+segment+s[end:]
 # Shadow variants are explicitly compiled in the adapted shadow passes.
 s=s.replace('#pragma vertex SChar_ShadowVert','#pragma multi_compile_shadowcaster\n            #pragma vertex SChar_ShadowVert')
 write(resources/f'Zmd{kind}.shader',stereo(s))

common=source/'Assets/Char/Texture/Common'
for name in ('T_actor_common_face_01_RD.png','T_actor_common_body_01_RD.png','T_actor_common_hair_01_RD.png','T_actor_common_female_face_01_cm_M.png','T_actor_common_face_01_hl_M.png','T_actor_common_hairline_03_M.png','T_actor_common_hairst_01_ST.png'):
 p=common/name;reference(p)
 target=resources/'Data'/f'{name}.bytes';target.parent.mkdir(parents=True,exist_ok=True)
 with target.open('xb') as f:f.write(p.read_bytes())
for name in ('ZmdRenderStyle.cs','ZmdRenderCapture.cs'):
 write(candidate/module/name,(lab/'Source'/name).read_text(encoding='utf8'))
write(lab/'source-study-manifest.json',json.dumps(study,indent=2,ensure_ascii=False))
# All destination files are new. The supplied ZMD project and current renderers
# remain untouched. Copy the current project, including the repaired grab code.
shutil.copytree(root/'Assets',project/'Assets')
shutil.copytree(root/'ProjectSettings',project/'ProjectSettings')
shutil.copytree(Path('H:/MGFR/HandGrabRepair-20261019/Project/Packages'),project/'Packages')
for p in candidate.rglob('*'):
 if p.is_file():
  dest=project/p.relative_to(candidate);dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb') as f:f.write(p.read_bytes())
write(project/'Assets/MGFR/Editor/ZmdRenderBuild.cs',(lab/'Source/ZmdRenderBuild.cs').read_text(encoding='utf8'))
print(project)
