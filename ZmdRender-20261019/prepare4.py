from pathlib import Path
import shutil
lab=Path(__file__).resolve().parent
old=lab/'Project3';project=lab/'Project4';candidate=lab/'Candidate4'
assert not project.exists() and not candidate.exists()
module=Path('Assets/MGFR/RenderStyles/ZmdEndfield');res=module/'Resources/ZmdEndfield'
changes={}
p=res/'ZmdBuiltInCompat.cginc';s=(old/p).read_text(encoding='utf8')
s=s.replace('#define TEXTURE2D_X_FLOAT(name) sampler2D name','#define TEXTURE2D_X_FLOAT(name) UNITY_DECLARE_DEPTH_TEXTURE(name)')
s=s.replace('#define SAMPLE_TEXTURE2D_X(tex,samp,uv) tex2D(tex,UnityStereoTransformScreenSpaceTex(uv))','#define SAMPLE_TEXTURE2D_X(tex,samp,uv) (SAMPLE_DEPTH_TEXTURE(tex,uv)).xxxx')
s=s.replace('float _ZmdExposure,_ZmdNormalScale;','float _ZmdExposure,_ZmdNormalScale;\nfloat3 _ZmdMainLightDirection,_ZmdMainLightColor,_ZmdAmbientColor;')
s=s.replace('return unitySampleShadow(p);','return lerp(.45,1,unitySampleShadow(p));')
s=s.replace('l.direction=normalize(_WorldSpaceLightPos0.xyz);l.color=_LightColor0.rgb;', 'l.direction=normalize(_ZmdMainLightDirection);l.color=_ZmdMainLightColor;')
s=s.replace('return max(ShadeSH9(float4(n,1)),half3(.08,.08,.09));','return _ZmdAmbientColor;')
changes[p]=s
p=module/'ZmdRenderStyle.cs';s=(old/p).read_text(encoding='utf8')
s=s.replace('new Color(.94f,.83f,.78f)','new Color(1f,.97f,.95f)').replace('new Color(.98f,.87f,.84f)','new Color(1f,.98f,.97f)')
s=s.replace('Set(material,"_DarkIntensity",1.55f)','Set(material,"_DarkIntensity",1.8f)')
s=s.replace('Set(material,"_TopLightIntensity",1.4f)','Set(material,"_TopLightIntensity",2.1f)')
s=s.replace('Set(material,"_SpecularIntensity",3.3f)','Set(material,"_SpecularIntensity",4.6f)')
s=s.replace('Set(material,"_AO_Offset",-.05f)','Set(material,"_AO_Offset",.04f)')
s=s.replace('  void UpdateGlobals()\n  {', '''  void UpdateGlobals()
  {
   if(key!=null){Shader.SetGlobalVector("_ZmdMainLightDirection",-key.transform.forward);Shader.SetGlobalVector("_ZmdMainLightColor",(Vector4)(key.color*key.intensity));}
   Shader.SetGlobalVector("_ZmdAmbientColor",new Vector4(.30f,.32f,.35f,1));''')
changes[p]=s
p=res/'ZmdHair.shader';s=(old/p).read_text(encoding='utf8').replace('half ao = saturate(maskMap.b + _AO_Offset);','half ao = lerp(1.0,saturate(maskMap.b + _AO_Offset),.65);')
changes[p]=s
p=module/'ZmdRenderCapture.cs';s=(old/p).read_text(encoding='utf8')
s=s.replace('   int magenta=0;', '   var composite=new Material(Resources.Load<Shader>("ZmdEndfield/ZmdComparison"));\n   int magenta=0;')
s=s.replace('var copy=variant==0?oldImage:newImage;Graphics.CopyTexture(image,copy);','var copy=variant==0?oldImage:newImage;copy.LoadRawTextureData(image.GetRawTextureData<byte>());copy.Apply();')
a='''    RenderTexture.active=pair;GL.Clear(true,true,Color.black);GL.PushMatrix();GL.LoadPixelMatrix(0,width*2,height,0);
    Graphics.DrawTexture(new Rect(0,0,width,height),oldImage);Graphics.DrawTexture(new Rect(width,0,width,height),newImage);GL.PopMatrix();'''
b='''    composite.SetTexture("_Before",oldImage);composite.SetTexture("_After",newImage);Graphics.Blit(null,pair,composite);
    RenderTexture.active=pair;'''
assert s.count(a)==1
s=s.replace(a,b)
changes[p]=s
def ignore(path,names):return [n for n in names if (Path(path)/n).relative_to(old) in changes]
shutil.copytree(old/'Assets',project/'Assets',ignore=ignore)
shutil.copytree(old/'ProjectSettings',project/'ProjectSettings')
shutil.copytree(old/'Packages',project/'Packages')
for p,s in changes.items():
 with (project/p).open('x',encoding='utf8') as f:f.write(s)
with (project/res/'ZmdComparison.shader').open('x',encoding='utf8') as f:f.write((lab/'Source/ZmdComparison.shader').read_text(encoding='utf8'))
shutil.copytree(project/module,candidate/module,ignore=shutil.ignore_patterns('*.meta'))
print(project)
