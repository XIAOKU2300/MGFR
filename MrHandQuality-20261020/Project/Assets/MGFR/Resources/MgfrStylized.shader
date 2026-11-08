Shader "MGFR/StylizedCharacter"
{
 Properties
 {
        _MrCoverage("MR semantic coverage",Float)=0
        _MrCutoff("MR cutout threshold",Range(0,1))=0.18

  _MainTex("Base",2D)="white"{}
  _Color("Tint",Color)=(1,1,1,1)
  _NormalData("RG normal data",2D)="gray"{}
  _PackedData("Authored detail regions",2D)="white"{}
  _FaceSDF("Face shading field",2D)="white"{}
  _FaceMask("Face region",2D)="white"{}
  _HairSpec("Hair highlight region",2D)="white"{}
  _MatCap("Reflection shape",2D)="black"{}
  _Kind("Material kind",Float)=3
  _NormalStrength("Normal strength",Float)=0
  _NormalY("Normal Y sign",Float)=-1
  _HasPacked("Packed region present",Float)=0
  _ShadowTint("Shadow colour",Color)=(.62,.68,.76,1)
  _LightTint("Light colour",Color)=(1,.98,.94,1)
  _ShadowThreshold("Band threshold",Float)=.50
  _Softness("Band softness",Float)=.14
  _Brightness("Material exposure",Float)=1
  _SpecStrength("Specular strength",Float)=.3
  _Roughness("Roughness",Float)=.6
  _MatCapStrength("Reflection strength",Float)=.1
  _OutlineWidth("Outline metres",Float)=.0007
  _OutlineTint("Outline colour",Color)=(.13,.17,.2,1)
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
   Name "STYLIZED_FORWARD"
   Tags {"LightMode"="ForwardBase"}
   Cull [_Cull] ZWrite [_ZWrite] Blend [_SrcBlend] [_DstBlend]
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_fwdbase
   #pragma multi_compile_instancing
   #pragma target 3.5
   #include "UnityCG.cginc"
   float _MrCoverage,_MrCutoff;
   #include "Lighting.cginc"
   #include "AutoLight.cginc"
   sampler2D _MainTex,_NormalData,_PackedData,_FaceSDF,_FaceMask,_HairSpec,_MatCap;
   float4 _MainTex_ST,_Color,_ShadowTint,_LightTint;
   float _Kind,_NormalStrength,_NormalY,_HasPacked,_ShadowThreshold,_Softness;
   float _Brightness,_SpecStrength,_Roughness,_MatCapStrength;
   float4 _SiHeadForward,_SiHeadRight,_SiHeadUp,_SiBodyUp;
   struct appdata
   {
    float4 vertex:POSITION;float3 normal:NORMAL;float4 tangent:TANGENT;float2 uv:TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
   };
   struct v2f
   {
    float4 pos:SV_POSITION;float2 uv:TEXCOORD0;
    float3 worldPos:TEXCOORD1;float3 normal:TEXCOORD2;float4 tangent:TEXCOORD3;
    SHADOW_COORDS(4)
    UNITY_VERTEX_OUTPUT_STEREO
   };
   v2f vert(appdata v)
   {
    v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_OUTPUT(v2f,o);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    o.pos=UnityObjectToClipPos(v.vertex);o.uv=TRANSFORM_TEX(v.uv,_MainTex);
    o.worldPos=mul(unity_ObjectToWorld,v.vertex).xyz;
    o.normal=UnityObjectToWorldNormal(v.normal);
    o.tangent=float4(UnityObjectToWorldDir(v.tangent.xyz),v.tangent.w*unity_WorldTransformParams.w);
    TRANSFER_SHADOW(o);return o;
   }
   float3 DecodeRG(float2 encoded,float strength)
   {
    float2 xy=(encoded*2-1)*float2(1,_NormalY)*strength;
    return normalize(float3(xy,sqrt(saturate(1-dot(xy,xy)))));
   }
   float4 frag(v2f i,float facing:VFACE):SV_Target
   {
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    float4 tex=tex2D(_MainTex,i.uv);float4 base=tex*_Color;
    if(_MrCoverage>.5){clip(base.a-_MrCutoff);base.a=1;}
    // Painted overlays, lashes and mouth keep their authored colour/alpha.
    if(_Kind>6.5)return base;
    float3 n=normalize(i.normal)*(facing>0?1:-1);
    float3 t=normalize(i.tangent.xyz);
    float3 b=normalize(cross(n,t))*i.tangent.w;
    float4 normalData=tex2D(_NormalData,i.uv);
    float3 mapped=DecodeRG(normalData.rg,_NormalStrength);
    n=normalize(t*mapped.x+b*mapped.y+n*mapped.z);
    float3 l=normalize(_WorldSpaceLightPos0.xyz);
    float3 v=normalize(UnityWorldSpaceViewDir(i.worldPos));
    float3 h=normalize(l+v);
    UNITY_LIGHT_ATTENUATION(atten,i,i.worldPos);
    float ndl=dot(n,l);
    float halfLambert=saturate(ndl*.5+.5);
    float band=lerp(halfLambert,smoothstep(_ShadowThreshold-_Softness,_ShadowThreshold+_Softness,halfLambert),.78);
    float4 packed=tex2D(_PackedData,i.uv);
    float ao=lerp(1,lerp(.86,1,packed.b),_HasPacked);
    float3 shade=lerp(_ShadowTint.rgb,_LightTint.rgb,band*atten);
    float metal=0,region=1;
    if(_Kind>2.5&&_Kind<4.5)
    {
     // Explicit warm-gold colour region for this character; no claim that the
     // source P texture has a universal Metallic/Roughness channel convention.
     float warm=smoothstep(.012,.10,tex.r-tex.b)*smoothstep(.005,.045,tex.g-tex.b);
     metal=max(warm*smoothstep(.035,.24,tex.r),smoothstep(.78,.96,packed.r)*_HasPacked*.72);
     region=lerp(1,.45+packed.r*.7,_HasPacked);
    }
    if(_Kind<.5)
    {
     float2 faceUV=i.uv;
     float side=dot(l,normalize(_SiHeadRight.xyz));
     if(side>0)faceUV.x=1-faceUV.x;
     float3 headUp=normalize(_SiHeadUp.xyz);
     float3 horizontalLight=l-headUp*dot(l,headUp);
     horizontalLight=normalize(horizontalLight+normalize(_SiHeadForward.xyz)*.0001);
     float front=dot(normalize(_SiHeadForward.xyz),horizontalLight);
     float threshold=1-(front*.5+.5);
     // B is used as this renderer's chosen continuous face field. R/G are
     // separate authored channels, not guessed to be material properties.
     float field=tex2D(_FaceSDF,faceUV).b;
     float faceLight=smoothstep(threshold-.07,threshold+.07,field);
     float mask=tex2D(_FaceMask,i.uv).r;
     float3 faceShade=lerp(_ShadowTint.rgb,_LightTint.rgb,faceLight);
     faceShade*=.89+.11*halfLambert;
     shade=lerp(shade,faceShade,mask);
    }
    float3 color=base.rgb*shade*ao*_Brightness;
    if(_Kind>4.5&&_Kind<5.5)
    {
     // Eye colour remains stable while its real iris geometry follows gaze.
     color=base.rgb*lerp(.86,1.08,saturate(ndl*.35+.65))*_Brightness;
    }
    float variance=length(ddx(n))+length(ddy(n));
    float rough=clamp(_Roughness+variance*.3,.26,1);
    float exponent=lerp(96,8,rough);
    float lightGate=smoothstep(-.05,.45,ndl);
    float spec=pow(saturate(dot(n,h)),exponent)*lightGate;
    float3 specColor=lerp(float3(.055,.055,.055),base.rgb*1.4,metal);
    color+=specColor*spec*_SpecStrength*region*lerp(1,3.0,metal)*_LightColor0.rgb;
    float3 up=_Kind>1.5&&_Kind<2.5?_SiHeadUp.xyz:_SiBodyUp.xyz;
    float3 right=normalize(cross(normalize(up),v)+float3(.00001,0,0));
    float3 viewUp=normalize(cross(v,right));
    float2 capUV=float2(dot(n,right),dot(n,viewUp))*.48+.5;
    float3 reflection=tex2D(_MatCap,capUV).rgb;
    float fresnel=pow(1-saturate(dot(n,v)),3);
    color+=reflection*_MatCapStrength*(.3+fresnel*.7)*lightGate*lerp(.25,1,metal);
    if(_Kind>1.5&&_Kind<2.5)
    {
     // A broad strand sheen and a narrower highlight have independent weights.
     float hairRegion=tex2D(_HairSpec,i.uv).r;
     float3 broadTS=DecodeRG(normalData.ba,.3);
     float3 broadN=normalize(t*broadTS.x+b*broadTS.y+normalize(i.normal)*broadTS.z);
     float broad=pow(saturate(dot(broadN,h)),16);
     float narrow=pow(saturate(dot(n,h)),56);
     color+=(broad*.075+narrow*.095)*lerp(.35,1,hairRegion)*lightGate*_SpecStrength*float3(.9,.96,1);
     color+=fresnel*.022*float3(.68,.84,.88)*saturate(ndl+.3);
    }
    // No full-screen tone map: the ALVR key background is never altered.
    return float4(color,base.a);
   }
   ENDCG
  }
  Pass
  {
   Name "FINE_OUTLINE"
   Tags {"LightMode"="Always"}
   Cull Front ZWrite Off ZTest LEqual Blend SrcAlpha OneMinusSrcAlpha
   CGPROGRAM
   #pragma vertex vert
   #pragma fragment frag
   #pragma multi_compile_instancing
   #pragma target 3.5
   #include "UnityCG.cginc"
   float _MrCoverage,_MrCutoff;
   sampler2D _MainTex;float4 _MainTex_ST,_Color,_OutlineTint;float _OutlineWidth;
   struct appdata {float4 vertex:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;UNITY_VERTEX_INPUT_INSTANCE_ID};
   struct v2f {float4 pos:SV_POSITION;float2 uv:TEXCOORD0;UNITY_VERTEX_OUTPUT_STEREO};
   v2f vert(appdata v)
   {
    v2f o;UNITY_SETUP_INSTANCE_ID(v);UNITY_INITIALIZE_OUTPUT(v2f,o);UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    float3 p=mul(unity_ObjectToWorld,v.vertex).xyz;
    p+=UnityObjectToWorldNormal(v.normal)*_OutlineWidth;
    o.pos=mul(UNITY_MATRIX_VP,float4(p,1));o.uv=TRANSFORM_TEX(v.uv,_MainTex);return o;
   }
   float4 frag(v2f i):SV_Target
   {
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    clip(_OutlineWidth-.000001);float alpha=tex2D(_MainTex,i.uv).a*_Color.a;clip(alpha-(_MrCoverage>.5?_MrCutoff:.55));
    return float4(_OutlineTint.rgb,_OutlineTint.a);
   }
   ENDCG
  }
 }
}
