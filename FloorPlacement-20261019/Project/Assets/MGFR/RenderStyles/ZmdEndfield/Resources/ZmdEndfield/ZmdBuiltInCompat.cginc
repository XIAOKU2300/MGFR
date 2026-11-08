#ifndef MGFR_ZMD_BUILTIN_COMPAT
#define MGFR_ZMD_BUILTIN_COMPAT
#include "UnityCG.cginc"
#include "Lighting.cginc"
#include "AutoLight.cginc"

// URP 14 -> Built-in adapter. The source material equations stay in their
// own shaders; this layer owns coordinate, shadow, texture and IBL differences.
#ifndef TEXTURE2D
#define TEXTURE2D(name) sampler2D name
#define SAMPLER(name)
#define SAMPLE_TEXTURE2D(tex,samp,uv) tex2D(tex,uv)
#define SAMPLE_TEXTURE2D_LOD(tex,samp,uv,lod) tex2Dlod(tex,float4(uv,0,lod))
#endif
#ifndef TEXTURE2D_X_FLOAT
#define TEXTURE2D_X_FLOAT(name) UNITY_DECLARE_DEPTH_TEXTURE(name)
#define SAMPLE_TEXTURE2D_X(tex,samp,uv) (SAMPLE_DEPTH_TEXTURE(tex,uv)).xxxx
#endif

float _ZmdExposure,_ZmdNormalScale;
float3 _ZmdMainLightDirection,_ZmdMainLightColor,_ZmdAmbientColor;
samplerCUBE _ZmdStudioCube;
struct VertexPositionInputs {float3 positionWS;float3 positionVS;float4 positionCS;float4 positionNDC;};
struct VertexNormalInputs {float3 normalWS;float3 tangentWS;float3 bitangentWS;};
float3 TransformObjectToWorld(float3 p){return mul(unity_ObjectToWorld,float4(p,1)).xyz;}
float3 TransformWorldToObject(float3 p){return mul(unity_WorldToObject,float4(p,1)).xyz;}
float4 TransformObjectToHClip(float3 p){return UnityObjectToClipPos(float4(p,1));}
float4 TransformWorldToHClip(float3 p){return mul(UNITY_MATRIX_VP,float4(p,1));}
float3 TransformObjectToWorldNormal(float3 n){return UnityObjectToWorldNormal(n);}
float3 TransformObjectToWorldDir(float3 d){return UnityObjectToWorldDir(d);}
float3 TransformWorldToView(float3 p){return mul(UNITY_MATRIX_V,float4(p,1)).xyz;}
float3 TransformWorldToViewDir(float3 n,bool normalized){float3 v=mul((float3x3)UNITY_MATRIX_V,n);return normalized?normalize(v):v;}
VertexPositionInputs GetVertexPositionInputs(float3 p)
{VertexPositionInputs o;o.positionWS=TransformObjectToWorld(p);o.positionVS=TransformWorldToView(o.positionWS);o.positionCS=TransformWorldToHClip(o.positionWS);o.positionNDC=ComputeScreenPos(o.positionCS);return o;}
VertexNormalInputs GetVertexNormalInputs(float3 n,float4 t)
{VertexNormalInputs o;o.normalWS=UnityObjectToWorldNormal(n);o.tangentWS=UnityObjectToWorldDir(t.xyz);o.bitangentWS=cross(o.normalWS,o.tangentWS)*t.w*unity_WorldTransformParams.w;return o;}
float3 GetWorldSpaceViewDir(float3 p){return UnityWorldSpaceViewDir(p);}
float4 GetShadowCoord(VertexPositionInputs p)
{
 #if defined(UNITY_NO_SCREENSPACE_SHADOWS)
 return mul(unity_WorldToShadow[0],float4(p.positionWS,1));
 #else
 return ComputeScreenPos(p.positionCS);
 #endif
}
float4 TransformWorldToShadowCoord(float3 p){VertexPositionInputs v=GetVertexPositionInputs(TransformWorldToObject(p));return GetShadowCoord(v);}
half ZmdScreenShadow(float4 p)
{
 #if defined(SHADOWS_SCREEN)
 return lerp(.45,1,unitySampleShadow(p));
 #else
 return 1;
 #endif
}
struct Light {half3 direction;half3 color;half shadowAttenuation;half distanceAttenuation;};
Light GetMainLight(float4 p)
{Light l;l.direction=normalize(_ZmdMainLightDirection);l.color=_ZmdMainLightColor;l.shadowAttenuation=ZmdScreenShadow(p);l.distanceAttenuation=1;return l;}
Light GetMainLight(){return GetMainLight(float4(0,0,0,1));}
half3 SampleSH(half3 n){return _ZmdAmbientColor;}
half3 GlossyEnvironmentReflection(float3 direction,float3 p,half roughness,half occlusion)
{return texCUBElod(_ZmdStudioCube,float4(direction,saturate(roughness)*6)).rgb*occlusion;}
float LinearEyeDepth(float z,float4 parameters){return rcp(parameters.z*z+parameters.w);}
half3 ZmdUnpackRG(half4 packed)
{half2 xy=(packed.rg*2-1)*half2(1,-1)*_ZmdNormalScale;return normalize(half3(xy,sqrt(saturate(1-dot(xy,xy)))));}
half3 ZmdFinish(half3 color)
{
 // Material-only shoulder: keep HDR hair and metal highlights controlled while
 // leaving the ALVR green clear colour and UI entirely outside tone mapping.
 float3 x=max(color,0)*max(_ZmdExposure,.01);
 return saturate((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14));
}
#endif
