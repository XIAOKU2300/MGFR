Shader "MGFR/EndfieldClothing"
{
 Properties
 {
  _MainTex("Base",2D)="white"{}
  _Color("Tint",Color)=(1,1,1,1)
  _NormalData("RG normals",2D)="gray"{}
  _PackedData("R metal G dielectric spec B AO A smoothness",2D)="white"{}
  _DiffuseRamp("Diffuse RGBA ramp",2D)="white"{}
  _SpecularRamp("Specular 2D ramp",2D)="white"{}
  _EmissionMap("Emission",2D)="black"{}
  _StudioCube("Studio reflection",Cube)="black"{}
  _NormalStrength("Normal strength",Float)=.4
  _NormalY("Normal Y",Float)=-1
  _Metallic("Metallic scale",Float)=1
  _SmoothnessScale("Smoothness scale",Float)=.9
  _OcclusionStrength("AO strength",Float)=.8
  _AmbientColor("Studio ambient",Color)=(.3,.32,.35,1)
  _SpecStrength("Direct specular",Float)=.75
  _ReflectionStrength("Environment specular",Float)=.65
  _EmissionStrength("Emission",Float)=.45
  _RampStrength("Ramp tint",Float)=.65
  _SpecRampFresnel("Specular ramp Fresnel blend",Float)=0
  _OutlineWidth("Outline metres",Float)=.0004
  _OutlineTint("Outline colour",Color)=(.14,.18,.2,.48)
  [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull",Float)=2
  [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend("Source blend",Float)=1
  [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend("Destination blend",Float)=0
  [Enum(Off,0,On,1)] _ZWrite("Depth write",Float)=1
 }
 SubShader
 {
  Tags {"RenderType"="Opaque" "IgnoreProjector"="True"}
  Pass
  {
   Name "ENDFIELD_CLOTHING"
   Tags {"LightMode"="ForwardBase"}
   Cull [_Cull] ZWrite [_ZWrite] Blend [_SrcBlend] [_DstBlend]
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_fwdbase
   #pragma multi_compile_instancing
   #pragma target 3.5
   #include "UnityCG.cginc"
   #include "Lighting.cginc"
   #include "AutoLight.cginc"
   sampler2D _MainTex,_NormalData,_PackedData,_DiffuseRamp,_SpecularRamp,_EmissionMap;
   samplerCUBE _StudioCube;
   float4 _MainTex_ST,_Color,_AmbientColor;
   float _NormalStrength,_NormalY,_Metallic,_SmoothnessScale,_OcclusionStrength;
   float _SpecStrength,_ReflectionStrength,_EmissionStrength,_RampStrength,_SpecRampFresnel;
   struct appdata
   {
    float4 vertex:POSITION;float3 normal:NORMAL;float4 tangent:TANGENT;float2 uv:TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
   };
   struct v2f
   {
    float4 pos:SV_POSITION;float2 uv:TEXCOORD0;float3 worldPos:TEXCOORD1;
    float3 normal:TEXCOORD2;float4 tangent:TEXCOORD3;
    SHADOW_COORDS(4)
    UNITY_VERTEX_OUTPUT_STEREO
   };
   v2f vert(appdata v)
   {
    v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_OUTPUT(v2f,o);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    o.pos=UnityObjectToClipPos(v.vertex);o.uv=TRANSFORM_TEX(v.uv,_MainTex);
    o.worldPos=mul(unity_ObjectToWorld,v.vertex).xyz;o.normal=UnityObjectToWorldNormal(v.normal);
    o.tangent=float4(UnityObjectToWorldDir(v.tangent.xyz),v.tangent.w*unity_WorldTransformParams.w);
    TRANSFER_SHADOW(o);return o;
   }
   float Luma(float3 c){return dot(c,float3(.2126,.7152,.0722));}
   float3 SaturationBoost(float3 c){return max(0,lerp(Luma(c).xxx,c,1.08));}
   float2 EnvironmentAB(float rough,float nv)
   {
    float4 r=rough*float4(-1,-.0275,-.572,.022)+float4(1,.0425,1.04,-.04);
    float a=min(r.x*r.x,exp2(-9.28*nv))*r.x+r.y;
    return float2(-1.04,1.04)*a+r.zw;
   }
   float4 frag(v2f i,float facing:VFACE):SV_Target
   {
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    float4 base=tex2D(_MainTex,i.uv)*_Color;
    float4 p=tex2D(_PackedData,i.uv);
    float metal=saturate(p.r*_Metallic),ao=lerp(1,p.b,_OcclusionStrength);
    float3 n=normalize(i.normal)*(facing>0?1:-1),t=normalize(i.tangent.xyz);
    float3 b=normalize(cross(n,t))*i.tangent.w;
    float2 xy=(tex2D(_NormalData,i.uv).rg*2-1)*float2(1,_NormalY)*_NormalStrength;
    float3 nts=normalize(float3(xy,sqrt(saturate(1-dot(xy,xy)))));
    n=normalize(t*nts.x+b*nts.y+n*nts.z);
    float3 v=normalize(UnityWorldSpaceViewDir(i.worldPos)),l=normalize(_WorldSpaceLightPos0.xyz);
    float nv=max(.001,saturate(dot(n,v))),nl=dot(n,l);
    UNITY_LIGHT_ATTENUATION(shadow,i,i.worldPos);
    float s=saturate(shadow);
    float pitch=smoothstep(0,1,saturate(2*(.75-abs(v.y))));
    float opposite=saturate(-dot(l.xz,v.xz)*rsqrt(max(dot(l.xz,l.xz)*dot(v.xz,v.xz),.00001)));
    float biased=clamp(nl+opposite*pitch*(.5-.5*nl*nl),-1,1);
    float4 ramp=tex2D(_DiffuseRamp,float2(biased*.5+.5,.5));
    // No view-light self-shadow map exists in this scene; authored AO supplies
    // small-scale occlusion. Scene-shadow attenuation is independent of it.
    float lit=min(ao,ramp.a);
    float3 liftedView=normalize(float3(v.x,min(1,v.y+.25),v.z));
    float viewLit=ao*tex2D(_DiffuseRamp,float2(dot(n,liftedView)*.5+.5,.5)).a;
    float3 diffuse=base.rgb*(1-.96*metal);
    float3 viewShade=lerp(.35*diffuse,SaturationBoost(diffuse),viewLit);
    float3 shadeBase=lerp(SaturationBoost(.65*.35*diffuse),.35*diffuse,saturate(viewLit+ramp.a));
    shadeBase=lerp(shadeBase,diffuse,lit);
    float range=max(ramp.r,max(ramp.g,ramp.b))-min(ramp.r,min(ramp.g,ramp.b));
    float3 rampShade=shadeBase*lerp(1,ramp.rgb,range*_RampStrength);
    // Preserve diffuse luminance while changing hue; the article's saturated
    // ratio cannot lift a darkening ramp, so use a bounded unsaturated ratio.
    rampShade*=min(2,Luma(shadeBase)/max(Luma(rampShade),.00001));
    float3 directLight=lerp(Luma(_LightColor0.rgb).xxx,_LightColor0.rgb,lit*s);
    float3 color=lerp(viewShade,rampShade,s)*(directLight+_AmbientColor.rgb);
    float variance=dot(ddx(n),ddx(n))+dot(ddy(n),ddy(n));
    float rough=clamp(sqrt(pow(1-p.a*_SmoothnessScale,2)+min(.12,variance)),.22,1);
    float alpha=max(rough*rough,.0078125),a2=alpha*alpha;
    float3 stylizedL=normalize(float3(v.x,lerp(.5,l.y,s),v.z));
    float3 h=normalize(s*l+2*stylizedL+v*(s+2));
    float nh=saturate(dot(n,h)),denom=nh*nh*(a2-1)+1;
    float d=a2/(denom*denom),visibility=rcp(4*nv+2*alpha);
    float2 specUV=float2(saturate(lerp(d*a2,nv*nv,_SpecRampFresnel)),rough*(1-metal));
    float3 specRamp=tex2D(_SpecularRamp,specUV).rgb;
    float3 f0=lerp((.04*p.g).xxx,base.rgb,metal);
    float w=lerp(viewLit,lit,s),weight=(w*.5+.5)*(w*.65+.35);
    float3 directSpec=min(max(d*visibility-.0001,0),20)*f0*specRamp*weight;
    color+=directSpec*_LightColor0.rgb*_SpecStrength;
    float3 iblF=lerp(f0,f0*specRamp,_SpecRampFresnel);
    float2 ab=EnvironmentAB(rough,nv);float ess=max(.05,ab.x+ab.y);
    float3 envBRDF=iblF*ab.x+saturate(50*iblF.g)*ab.y;
    float3 reflected=texCUBElod(_StudioCube,float4(reflect(-v,n),rough*6)).rgb;
    color+=reflected*envBRDF*(1+iblF*(1-ess)/ess)*ao*_ReflectionStrength;
    color+=tex2D(_EmissionMap,i.uv).rgb*_EmissionStrength;
    return float4(color,base.a);
   }
   ENDCG
  }
  UsePass "MGFR/StylizedCharacter/FINE_OUTLINE"
 }
}
