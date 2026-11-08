// File: Assets/MGFR/Shaders/MgfrCharacter.shader
static const int INSTANCING_ON = 0;
static const int DIRECTIONAL = 0;
static const int LIGHTPROBE_SH = 0;
static const int SHADOWS_SHADOWMASK = 0;
static const int DYNAMICLIGHTMAP_ON = 0;
static const int LIGHTMAP_ON = 0;
static const int LIGHTMAP_SHADOW_MIXING = 0;
static const int DIRLIGHTMAP_COMBINED = 0;
static const int SHADOWS_SCREEN = 0;
static const int VERTEXLIGHT_ON = 0;
static const int UNITY_NO_DXT5nm = 0;
static const int UNITY_FRAMEBUFFER_FETCH_AVAILABLE = 0;
static const int UNITY_METAL_SHADOWS_USE_POINT_FILTERING = 0;
static const int UNITY_NO_SCREENSPACE_SHADOWS = 0;
static const int UNITY_PBS_USE_BRDF2 = 0;
static const int UNITY_PBS_USE_BRDF3 = 0;
static const int UNITY_HARDWARE_TIER1 = 0;
static const int UNITY_HARDWARE_TIER2 = 0;
static const int UNITY_HARDWARE_TIER3 = 0;
static const int UNITY_COLORSPACE_GAMMA = 0;
static const int UNITY_LIGHTMAP_DLDR_ENCODING = 0;
static const int UNITY_LIGHTMAP_RGBM_ENCODING = 0;
static const int UNITY_VIRTUAL_TEXTURING = 0;
static const int UNITY_PRETRANSFORM_TO_DISPLAY_ORIENTATION = 0;
static const int UNITY_ASTC_NORMALMAP_ENCODING = 0;
static const int SHADER_API_GLES30 = 0;
static const int SHADER_API_GLES31 = 0;
static const int SHADER_API_GLES32 = 0;
static const int UNITY_UNIFIED_SHADER_PRECISION_MODEL = 0;
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/HLSLSupport.cginc
#pragma warning ( disable : 3205 )
#pragma warning ( disable : 3568 )
#pragma warning ( disable : 3571 )
#pragma warning ( disable : 3206 )
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityShaderVariables.cginc
cbuffer UnityPerCamera {
	float4 _Time;
	float4 _SinTime;
	float4 _CosTime;
	float4 unity_DeltaTime;
	float4 _ProjectionParams;
	float4 _ScreenParams;
	float4 _ZBufferParams;
	float4 unity_OrthoParams;
};
cbuffer UnityPerCameraRare {
	float4 unity_CameraWorldClipPlanes [6];
};
cbuffer UnityLighting {
	float4 _WorldSpaceLightPos0;
	float4 _LightPositionRange;
	float4 _LightProjectionParams;
	float4 unity_4LightPosX0;
	float4 unity_4LightPosY0;
	float4 unity_4LightPosZ0;
	half4 unity_4LightAtten0;
	half4 unity_LightColor [8];
	float4 unity_LightPosition [8];
	half4 unity_LightAtten [8];
	float4 unity_SpotDirection [8];
	half4 unity_SHAr;
	half4 unity_SHAg;
	half4 unity_SHAb;
	half4 unity_SHBr;
	half4 unity_SHBg;
	half4 unity_SHBb;
	half4 unity_SHC;
	half4 unity_OcclusionMaskSelector;
	half4 unity_ProbesOcclusion;
};
cbuffer UnityLightingOld {
	half3 unity_LightColor0, unity_LightColor1, unity_LightColor2, unity_LightColor3;
};
cbuffer UnityShadows {
	float4 unity_ShadowSplitSpheres [4];
	float4 unity_ShadowSplitSqRadii;
	float4 unity_LightShadowBias;
	float4 _LightSplitsNear;
	float4 _LightSplitsFar;
	float4x4 unity_WorldToShadow [4];
	float4 _LightShadowData;
	float4 unity_ShadowFadeCenterAndType;
};
cbuffer UnityPerDraw {
	float4x4 unity_ObjectToWorld;
	float4x4 unity_WorldToObject;
	float4 unity_LODFade;
	float4 unity_WorldTransformParams;
	float4 unity_RenderingLayer;
};
cbuffer UnityStereoGlobals {
	float4x4 unity_StereoMatrixP [2];
	float4x4 unity_StereoMatrixV [2];
	float4x4 unity_StereoMatrixInvV [2];
	float4x4 unity_StereoMatrixVP [2];
	float4x4 unity_StereoCameraProjection [2];
	float4x4 unity_StereoCameraInvProjection [2];
	float4x4 unity_StereoWorldToCamera [2];
	float4x4 unity_StereoCameraToWorld [2];
	float3 unity_StereoWorldSpaceCameraPos [2];
	float4 unity_StereoScaleOffset [2];
};
static uint unity_StereoEyeIndex;
cbuffer UnityPerDrawRare {
	float4x4 glstate_matrix_transpose_modelview0;
};
cbuffer UnityPerFrame {
	half4 glstate_lightmodel_ambient;
	half4 unity_AmbientSky;
	half4 unity_AmbientEquator;
	half4 unity_AmbientGround;
	half4 unity_IndirectSpecColor;
	half4 unity_ShadowColor;
};
cbuffer UnityFog {
	half4 unity_FogColor;
	float4 unity_FogParams;
};
Texture2D unity_Lightmap; SamplerState samplerunity_Lightmap;
Texture2D unity_LightmapInd;
Texture2D unity_ShadowMask; SamplerState samplerunity_ShadowMask;
Texture2D unity_DynamicLightmap; SamplerState samplerunity_DynamicLightmap;
Texture2D unity_DynamicDirectionality;
Texture2D unity_DynamicNormal;
cbuffer UnityLightmaps {
	float4 unity_LightmapST;
	float4 unity_DynamicLightmapST;
};
TextureCube unity_SpecCube0; SamplerState samplerunity_SpecCube0;
TextureCube unity_SpecCube1;
cbuffer UnityReflectionProbes {
	float4 unity_SpecCube0_BoxMax;
	float4 unity_SpecCube0_BoxMin;
	float4 unity_SpecCube0_ProbePosition;
	half4 unity_SpecCube0_HDR;
	float4 unity_SpecCube1_BoxMax;
	float4 unity_SpecCube1_BoxMin;
	float4 unity_SpecCube1_ProbePosition;
	half4 unity_SpecCube1_HDR;
};
Texture3D unity_ProbeVolumeSH; SamplerState samplerunity_ProbeVolumeSH;
cbuffer UnityProbeVolume {
	float4 unity_ProbeVolumeParams;
	float4x4 unity_ProbeVolumeWorldToObject;
	float3 unity_ProbeVolumeSizeInv;
	float3 unity_ProbeVolumeMin;
};
static float4x4 unity_MatrixMVP = mul (unity_StereoMatrixVP [unity_StereoEyeIndex], unity_ObjectToWorld);
static float4x4 unity_MatrixMV = mul (unity_StereoMatrixV [unity_StereoEyeIndex], unity_ObjectToWorld);
static float4x4 unity_MatrixTMV = transpose (unity_MatrixMV);
static float4x4 unity_MatrixITMV = transpose (mul (unity_WorldToObject, unity_StereoMatrixInvV [unity_StereoEyeIndex]));
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityShaderUtilities.cginc
float3 ODSOffset (float3 worldPos, float ipd)
{
	const float EPSILON = 2.4414e-4;
	float3 worldUp = float3 (0.0, 1.0, 0.0);
	float3 camOffset = worldPos . xyz - unity_StereoWorldSpaceCameraPos [unity_StereoEyeIndex] . xyz;
	float4 direction = float4 (camOffset . xyz, dot (camOffset . xyz, camOffset . xyz));
	direction . w = max (EPSILON, direction . w);
	direction *= rsqrt (direction . w);
	float3 tangent = cross (direction . xyz, worldUp . xyz);
	if (dot (tangent, tangent) < EPSILON)
	return float3 (0, 0, 0);
	tangent = normalize (tangent);
	float directionMinusIPD = max (EPSILON, direction . w * direction . w - ipd * ipd);
	float a = ipd * ipd / direction . w;
	float b = ipd / direction . w * sqrt (directionMinusIPD);
	float3 offset = - a * direction . xyz + b * tangent;
	return offset;
}
inline float4 UnityObjectToClipPosODS (float3 inPos)
{
	float4 clipPos;
	float3 posWorld = mul (unity_ObjectToWorld, float4 (inPos, 1.0)) . xyz;
	clipPos = mul (unity_StereoMatrixVP [unity_StereoEyeIndex], float4 (posWorld, 1.0));
	return clipPos;
}
inline float4 UnityObjectToClipPos (in float3 pos)
{
	return mul (unity_StereoMatrixVP [unity_StereoEyeIndex], mul (unity_ObjectToWorld, float4 (pos, 1.0)));
}
inline float4 UnityObjectToClipPos (float4 pos)
{
	return UnityObjectToClipPos (pos . xyz);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityInstancing.cginc
static uint unity_InstanceID;
cbuffer UnityDrawCallInfo {
	int unity_BaseInstanceID;
	int unity_InstanceCount;
};
void UnitySetupInstanceID (uint inputInstanceID)
{
	unity_StereoEyeIndex = inputInstanceID & 0x01;
	unity_InstanceID = unity_BaseInstanceID + (inputInstanceID >> 1);
}
void UnitySetupCompoundMatrices ();
static float4x4 unity_MatrixMVP_Instanced;
static float4x4 unity_MatrixMV_Instanced;
static float4x4 unity_MatrixTMV_Instanced;
static float4x4 unity_MatrixITMV_Instanced;
void UnitySetupCompoundMatrices ()
{
	unity_MatrixMVP_Instanced = mul (unity_StereoMatrixVP [unity_StereoEyeIndex], unity_ObjectToWorld);
	unity_MatrixMV_Instanced = mul (unity_StereoMatrixV [unity_StereoEyeIndex], unity_ObjectToWorld);
	unity_MatrixTMV_Instanced = transpose (unity_MatrixMV_Instanced);
	unity_MatrixITMV_Instanced = transpose (mul (unity_WorldToObject, unity_StereoMatrixInvV [unity_StereoEyeIndex]));
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityCG.cginc
struct appdata_base {
	float4 vertex : POSITION;
	float3 normal : NORMAL;
	float4 texcoord : TEXCOORD0;
	uint instanceID : SV_InstanceID;
};
struct appdata_tan {
	float4 vertex : POSITION;
	float4 tangent : TANGENT;
	float3 normal : NORMAL;
	float4 texcoord : TEXCOORD0;
	uint instanceID : SV_InstanceID;
};
struct appdata_full {
	float4 vertex : POSITION;
	float4 tangent : TANGENT;
	float3 normal : NORMAL;
	float4 texcoord : TEXCOORD0;
	float4 texcoord1 : TEXCOORD1;
	float4 texcoord2 : TEXCOORD2;
	float4 texcoord3 : TEXCOORD3;
	half4 color : COLOR;
	uint instanceID : SV_InstanceID;
};
inline bool IsGammaSpace ()
{
	return false;
}
inline float GammaToLinearSpaceExact (float value)
{
	if (value <= 0.04045F)
	return value / 12.92F;
	else if (value < 1.0F)
	return pow ((value + 0.055F) / 1.055F, 2.4F);
	else
	return pow (value, 2.2F);
}
inline half3 GammaToLinearSpace (half3 sRGB)
{
	return sRGB * (sRGB * (sRGB * 0.305306011h + 0.682171111h) + 0.012522878h);
}
inline float LinearToGammaSpaceExact (float value)
{
	if (value <= 0.0F)
	return 0.0F;
	else if (value <= 0.0031308F)
	return 12.92F * value;
	else if (value < 1.0F)
	return 1.055F * pow (value, 0.4166667F) - 0.055F;
	else
	return pow (value, 0.45454545F);
}
inline half3 LinearToGammaSpace (half3 linRGB)
{
	linRGB = max (linRGB, half3 (0.h, 0.h, 0.h));
	return max (1.055h * pow (linRGB, 0.416666667h) - 0.055h, 0.h);
}
inline float4 UnityWorldToClipPos (in float3 pos)
{
	return mul (unity_StereoMatrixVP [unity_StereoEyeIndex], float4 (pos, 1.0));
}
inline float4 UnityViewToClipPos (in float3 pos)
{
	return mul (unity_StereoMatrixP [unity_StereoEyeIndex], float4 (pos, 1.0));
}
inline float3 UnityObjectToViewPos (in float3 pos)
{
	return mul (unity_StereoMatrixV [unity_StereoEyeIndex], mul (unity_ObjectToWorld, float4 (pos, 1.0))) . xyz;
}
inline float3 UnityObjectToViewPos (float4 pos)
{
	return UnityObjectToViewPos (pos . xyz);
}
inline float3 UnityWorldToViewPos (in float3 pos)
{
	return mul (unity_StereoMatrixV [unity_StereoEyeIndex], float4 (pos, 1.0)) . xyz;
}
inline float3 UnityObjectToWorldDir (in float3 dir)
{
	return normalize (mul ((float3x3) unity_ObjectToWorld, dir));
}
inline float3 UnityWorldToObjectDir (in float3 dir)
{
	return normalize (mul ((float3x3) unity_WorldToObject, dir));
}
inline float3 UnityObjectToWorldNormal (in float3 norm)
{
	return normalize (mul (norm, (float3x3) unity_WorldToObject));
}
inline float3 UnityWorldSpaceLightDir (in float3 worldPos)
{
	return _WorldSpaceLightPos0 . xyz - worldPos * _WorldSpaceLightPos0 . w;
}
inline float3 WorldSpaceLightDir (in float4 localPos)
{
	float3 worldPos = mul (unity_ObjectToWorld, localPos) . xyz;
	return UnityWorldSpaceLightDir (worldPos);
}
inline float3 ObjSpaceLightDir (in float4 v)
{
	float3 objSpaceLightPos = mul (unity_WorldToObject, _WorldSpaceLightPos0) . xyz;
	return objSpaceLightPos . xyz - v . xyz * _WorldSpaceLightPos0 . w;
}
inline float3 UnityWorldSpaceViewDir (in float3 worldPos)
{
	return unity_StereoWorldSpaceCameraPos [unity_StereoEyeIndex] . xyz - worldPos;
}
inline float3 WorldSpaceViewDir (in float4 localPos)
{
	float3 worldPos = mul (unity_ObjectToWorld, localPos) . xyz;
	return UnityWorldSpaceViewDir (worldPos);
}
inline float3 ObjSpaceViewDir (in float4 v)
{
	float3 objSpaceCameraPos = mul (unity_WorldToObject, float4 (unity_StereoWorldSpaceCameraPos [unity_StereoEyeIndex] . xyz, 1)) . xyz;
	return objSpaceCameraPos - v . xyz;
}
float3 Shade4PointLights (
float4 lightPosX, float4 lightPosY, float4 lightPosZ,
float3 lightColor0, float3 lightColor1, float3 lightColor2, float3 lightColor3,
float4 lightAttenSq,
float3 pos, float3 normal)
{
	float4 toLightX = lightPosX - pos . x;
	float4 toLightY = lightPosY - pos . y;
	float4 toLightZ = lightPosZ - pos . z;
	float4 lengthSq = 0;
	lengthSq += toLightX * toLightX;
	lengthSq += toLightY * toLightY;
	lengthSq += toLightZ * toLightZ;
	lengthSq = max (lengthSq, 0.000001);
	float4 ndotl = 0;
	ndotl += toLightX * normal . x;
	ndotl += toLightY * normal . y;
	ndotl += toLightZ * normal . z;
	float4 corr = rsqrt (lengthSq);
	ndotl = max (float4 (0, 0, 0, 0), ndotl * corr);
	float4 atten = 1.0 / (1.0 + lengthSq * lightAttenSq);
	float4 diff = ndotl * atten;
	float3 col = 0;
	col += lightColor0 * diff . x;
	col += lightColor1 * diff . y;
	col += lightColor2 * diff . z;
	col += lightColor3 * diff . w;
	return col;
}
float3 ShadeVertexLightsFull (float4 vertex, float3 normal, int lightCount, bool spotLight)
{
	float3 viewpos = UnityObjectToViewPos (vertex . xyz);
	float3 viewN = normalize (mul ((float3x3) unity_MatrixITMV_Instanced, normal));
	float3 lightColor = (glstate_lightmodel_ambient * 2) . xyz;
	for (int i = 0; i < lightCount; i ++) {
		float3 toLight = unity_LightPosition [i] . xyz - viewpos . xyz * unity_LightPosition [i] . w;
		float lengthSq = dot (toLight, toLight);
		lengthSq = max (lengthSq, 0.000001);
		toLight *= rsqrt (lengthSq);
		float atten = 1.0 / (1.0 + lengthSq * unity_LightAtten [i] . z);
		if (spotLight)
		{
			float rho = max (0, dot (toLight, unity_SpotDirection [i] . xyz));
			float spotAtt = (rho - unity_LightAtten [i] . x) * unity_LightAtten [i] . y;
			atten *= saturate (spotAtt);
		}
		float diff = max (0, dot (viewN, toLight));
		lightColor += unity_LightColor [i] . rgb * (diff * atten);
	}
	return lightColor;
}
float3 ShadeVertexLights (float4 vertex, float3 normal)
{
	return ShadeVertexLightsFull (vertex, normal, 4, false);
}
half3 SHEvalLinearL0L1 (half4 normal)
{
	half3 x;
	x . r = dot (unity_SHAr, normal);
	x . g = dot (unity_SHAg, normal);
	x . b = dot (unity_SHAb, normal);
	return x;
}
half3 SHEvalLinearL2 (half4 normal)
{
	half3 x1, x2;
	half4 vB = normal . xyzz * normal . yzzx;
	x1 . r = dot (unity_SHBr, vB);
	x1 . g = dot (unity_SHBg, vB);
	x1 . b = dot (unity_SHBb, vB);
	half vC = normal . x * normal . x - normal . y * normal . y;
	x2 = unity_SHC . rgb * vC;
	return x1 + x2;
}
half3 ShadeSH9 (half4 normal)
{
	half3 res = SHEvalLinearL0L1 (normal);
	res += SHEvalLinearL2 (normal);
	return res;
}
half3 ShadeSH3Order (half4 normal)
{
	half3 res = SHEvalLinearL2 (normal);
	return res;
}
half3 SHEvalLinearL0L1_SampleProbeVolume (half4 normal, float3 worldPos)
{
	const float transformToLocal = unity_ProbeVolumeParams . y;
	const float texelSizeX = unity_ProbeVolumeParams . z;
	float3 position = (transformToLocal == 1.0f) ? mul (unity_ProbeVolumeWorldToObject, float4 (worldPos, 1.0)) . xyz : worldPos;
	float3 texCoord = (position - unity_ProbeVolumeMin . xyz) * unity_ProbeVolumeSizeInv . xyz;
	texCoord . x = texCoord . x * 0.25f;
	float texCoordX = clamp (texCoord . x, 0.5f * texelSizeX, 0.25f - 0.5f * texelSizeX);
	texCoord . x = texCoordX;
	half4 SHAr = unity_ProbeVolumeSH . Sample (samplerunity_ProbeVolumeSH, texCoord);
	texCoord . x = texCoordX + 0.25f;
	half4 SHAg = unity_ProbeVolumeSH . Sample (samplerunity_ProbeVolumeSH, texCoord);
	texCoord . x = texCoordX + 0.5f;
	half4 SHAb = unity_ProbeVolumeSH . Sample (samplerunity_ProbeVolumeSH, texCoord);
	half3 x1;
	x1 . r = dot (SHAr, normal);
	x1 . g = dot (SHAg, normal);
	x1 . b = dot (SHAb, normal);
	return x1;
}
half3 ShadeSH12Order (half4 normal)
{
	half3 res = SHEvalLinearL0L1 (normal);
	return res;
}
struct v2f_vertex_lit {
	float2 uv : TEXCOORD0;
	half4 diff : COLOR0;
	half4 spec : COLOR1;
};
inline half4 VertexLight (v2f_vertex_lit i, sampler2D mainTex)
{
	half4 texcol = tex2D (mainTex, i . uv);
	half4 c;
	c . xyz = (texcol . xyz * i . diff . xyz + i . spec . xyz * texcol . a);
	c . w = texcol . w * i . diff . w;
	return c;
}
inline float2 ParallaxOffset (half h, half height, half3 viewDir)
{
	h = h * height - height / 2.0;
	float3 v = normalize (viewDir);
	v . z += 0.42;
	return h * (v . xy / v . z);
}
inline half Luminance (half3 rgb)
{
	return dot (rgb, half4 (0.0396819152, 0.458021790, 0.00609653955, 1.0) . rgb);
}
half LinearRgbToLuminance (half3 linearRgb)
{
	return dot (linearRgb, half3 (0.2126729f, 0.7151522f, 0.0721750f));
}
half4 UnityEncodeRGBM (half3 color, float maxRGBM)
{
	float kOneOverRGBMMaxRange = 1.0 / maxRGBM;
	const float kMinMultiplier = 2.0 * 1e-2;
	float3 rgb = color * kOneOverRGBMMaxRange;
	float alpha = max (max (rgb . r, rgb . g), max (rgb . b, kMinMultiplier));
	alpha = ceil (alpha * 255.0) / 255.0;
	alpha = max (alpha, kMinMultiplier);
	return half4 (rgb / alpha, alpha);
}
inline half3 DecodeHDR (half4 data, half4 decodeInstructions, int colorspaceIsGamma)
{
	half alpha = decodeInstructions . w * (data . a - 1.0) + 1.0;
	if (colorspaceIsGamma)
	return (decodeInstructions . x * alpha) * data . rgb;
	return (decodeInstructions . x * pow (alpha, decodeInstructions . y)) * data . rgb;
}
inline half3 DecodeHDR (half4 data, half4 decodeInstructions)
{
	return DecodeHDR (data, decodeInstructions, 0);
}
inline half3 DecodeLightmapRGBM (half4 data, half4 decodeInstructions)
{
	return (decodeInstructions . x * pow (data . a, decodeInstructions . y)) * data . rgb;
}
inline half3 DecodeLightmapDoubleLDR (half4 color, half4 decodeInstructions)
{
	return decodeInstructions . x * color . rgb;
}
inline half3 DecodeLightmap (half4 color, half4 decodeInstructions)
{
	return color . rgb;
}
half4 unity_Lightmap_HDR;
inline half3 DecodeLightmap (half4 color)
{
	return DecodeLightmap (color, unity_Lightmap_HDR);
}
half4 unity_DynamicLightmap_HDR;
inline half3 DecodeRealtimeLightmap (half4 color)
{
	return pow ((unity_DynamicLightmap_HDR . x * color . a) * color . rgb, unity_DynamicLightmap_HDR . y);
}
inline half3 DecodeDirectionalLightmap (half3 color, half4 dirTex, half3 normalWorld)
{
	half halfLambert = dot (normalWorld, dirTex . xyz - 0.5) + 0.5;
	return color * halfLambert / max (1e-4h, dirTex . w);
}
inline float4 EncodeFloatRGBA (float v)
{
	float4 kEncodeMul = float4 (1.0, 255.0, 65025.0, 16581375.0);
	float kEncodeBit = 1.0 / 255.0;
	float4 enc = kEncodeMul * v;
	enc = frac (enc);
	enc -= enc . yzww * kEncodeBit;
	return enc;
}
inline float DecodeFloatRGBA (float4 enc)
{
	float4 kDecodeDot = float4 (1.0, 1 / 255.0, 1 / 65025.0, 1 / 16581375.0);
	return dot (enc, kDecodeDot);
}
inline float2 EncodeFloatRG (float v)
{
	float2 kEncodeMul = float2 (1.0, 255.0);
	float kEncodeBit = 1.0 / 255.0;
	float2 enc = kEncodeMul * v;
	enc = frac (enc);
	enc . x -= enc . y * kEncodeBit;
	return enc;
}
inline float DecodeFloatRG (float2 enc)
{
	float2 kDecodeDot = float2 (1.0, 1 / 255.0);
	return dot (enc, kDecodeDot);
}
inline float2 EncodeViewNormalStereo (float3 n)
{
	float kScale = 1.7777;
	float2 enc;
	enc = n . xy / (n . z + 1);
	enc /= kScale;
	enc = enc * 0.5 + 0.5;
	return enc;
}
inline float3 DecodeViewNormalStereo (float4 enc4)
{
	float kScale = 1.7777;
	float3 nn = enc4 . xyz * float3 (2 * kScale, 2 * kScale, 0) + float3 (- kScale, - kScale, 1);
	float g = 2.0 / dot (nn . xyz, nn . xyz);
	float3 n;
	n . xy = g * nn . xy;
	n . z = g - 1;
	return n;
}
inline float4 EncodeDepthNormal (float depth, float3 normal)
{
	float4 enc;
	enc . xy = EncodeViewNormalStereo (normal);
	enc . zw = EncodeFloatRG (depth);
	return enc;
}
inline void DecodeDepthNormal (float4 enc, out float depth, out float3 normal)
{
	depth = DecodeFloatRG (enc . zw);
	normal = DecodeViewNormalStereo (enc);
}
inline half3 UnpackNormalDXT5nm (half4 packednormal)
{
	half3 normal;
	normal . xy = packednormal . wy * 2 - 1;
	normal . z = sqrt (1 - saturate (dot (normal . xy, normal . xy)));
	return normal;
}
half3 UnpackNormalmapRGorAG (half4 packednormal)
{
	packednormal . x *= packednormal . w;
	half3 normal;
	normal . xy = packednormal . xy * 2 - 1;
	normal . z = sqrt (1 - saturate (dot (normal . xy, normal . xy)));
	return normal;
}
inline half3 UnpackNormal (half4 packednormal)
{
	return UnpackNormalmapRGorAG (packednormal);
}
half3 UnpackNormalWithScale (half4 packednormal, float scale)
{
	packednormal . x *= packednormal . w;
	half3 normal;
	normal . xy = (packednormal . xy * 2 - 1) * scale;
	normal . z = sqrt (1 - saturate (dot (normal . xy, normal . xy)));
	return normal;
}
inline float Linear01Depth (float z)
{
	return 1.0 / (_ZBufferParams . x * z + _ZBufferParams . y);
}
inline float LinearEyeDepth (float z)
{
	return 1.0 / (_ZBufferParams . z * z + _ZBufferParams . w);
}
inline float2 UnityStereoScreenSpaceUVAdjustInternal (float2 uv, float4 scaleAndOffset)
{
	return uv . xy * scaleAndOffset . xy + scaleAndOffset . zw;
}
inline float4 UnityStereoScreenSpaceUVAdjustInternal (float4 uv, float4 scaleAndOffset)
{
	return float4 (UnityStereoScreenSpaceUVAdjustInternal (uv . xy, scaleAndOffset), UnityStereoScreenSpaceUVAdjustInternal (uv . zw, scaleAndOffset));
}
struct appdata_img
{
	float4 vertex : POSITION;
	half2 texcoord : TEXCOORD0;
	uint instanceID : SV_InstanceID;
};
struct v2f_img
{
	float4 pos : SV_POSITION;
	half2 uv : TEXCOORD0;
	uint instanceID : SV_InstanceID;
	uint stereoTargetEyeIndex : SV_RenderTargetArrayIndex;
};
float2 MultiplyUV (float4x4 mat, float2 inUV) {
	float4 temp = float4 (inUV . x, inUV . y, 0, 0);
	temp = mul (mat, temp);
	return temp . xy;
}
v2f_img vert_img (appdata_img v)
{
	v2f_img o;
	o = (v2f_img) 0;;
	{UnitySetupInstanceID (v . instanceID); UnitySetupCompoundMatrices ();};
	o . stereoTargetEyeIndex = unity_StereoEyeIndex;
	o . pos = UnityObjectToClipPos (v . vertex);
	o . uv = v . texcoord;
	return o;
}
inline float4 ComputeNonStereoScreenPos (float4 pos) {
	float4 o = pos * 0.5f;
	o . xy = float2 (o . x, o . y * _ProjectionParams . x) + o . w;
	o . zw = pos . zw;
	return o;
}
inline float4 ComputeScreenPos (float4 pos) {
	float4 o = ComputeNonStereoScreenPos (pos);
	return o;
}
inline float4 ComputeGrabScreenPos (float4 pos) {
	float scale = - 1.0;
	float4 o = pos * 0.5f;
	o . xy = float2 (o . x, o . y * scale) + o . w;
	o . zw = pos . zw;
	return o;
}
inline float4 UnityPixelSnap (float4 pos)
{
	float2 hpc = _ScreenParams . xy * 0.5f;
	float2 pixelPos = round ((pos . xy / pos . w) * hpc);
	pos . xy = pixelPos / hpc * pos . w;
	return pos;
}
inline float2 TransformViewToProjection (float2 v) {
	return mul ((float2x2) unity_StereoMatrixP [unity_StereoEyeIndex], v);
}
inline float3 TransformViewToProjection (float3 v) {
	return mul ((float3x3) unity_StereoMatrixP [unity_StereoEyeIndex], v);
}
float4 UnityEncodeCubeShadowDepth (float z)
{
	return z;
}
float UnityDecodeCubeShadowDepth (float4 vals)
{
	return vals . r;
}
float4 UnityClipSpaceShadowCasterPos (float4 vertex, float3 normal)
{
	float4 wPos = mul (unity_ObjectToWorld, vertex);
	if (unity_LightShadowBias . z != 0.0)
	{
		float3 wNormal = UnityObjectToWorldNormal (normal);
		float3 wLight = normalize (UnityWorldSpaceLightDir (wPos . xyz));
		float shadowCos = dot (wNormal, wLight);
		float shadowSine = sqrt (1 - shadowCos * shadowCos);
		float normalBias = unity_LightShadowBias . z * shadowSine;
		wPos . xyz -= wNormal * normalBias;
	}
	return mul (unity_StereoMatrixVP [unity_StereoEyeIndex], wPos);
}
float4 UnityClipSpaceShadowCasterPos (float3 vertex, float3 normal)
{
	return UnityClipSpaceShadowCasterPos (float4 (vertex, 1), normal);
}
float4 UnityApplyLinearShadowBias (float4 clipPos)
{
	clipPos . z += max (- 1, min (unity_LightShadowBias . x / clipPos . w, 0));
	float clamped = min (clipPos . z, clipPos . w * (1.0));
	clipPos . z = lerp (clipPos . z, clamped, unity_LightShadowBias . y);
	return clipPos;
}
float4 PackHeightmap (float height)
{
	return height;
}
float UnpackHeightmap (float4 height)
{
	return height . r;
}
// File: Assets/RepairCoverage.cginc
float _MGFRRgbKeyCoverage;
float _MGFRRgbKeyCoverageCell;
float2 MgfrCoverageUV (float2 uv, float2 pixel)
{
	float cell = max (2, _MGFRRgbKeyCoverageCell);
	float2 delta = (floor (pixel / cell) + .5) * cell - pixel;
	return uv + ddx (uv) * delta . x + ddy (uv) * delta . y;
}
float MgfrCoverageAlpha (float alpha, float2 pixel)
{
	if (_MGFRRgbKeyCoverage < .5) return alpha;
	uint2 p = (uint2) floor (pixel / max (2, _MGFRRgbKeyCoverageCell));
	const float bayer [16] = {0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5};
	float threshold = (bayer [(p . y & 3) * 4 + (p . x & 3)] + .5) / 16;
	clip (saturate (alpha) - threshold);
	return 1;
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityLightingCommon.cginc
half4 _LightColor0;
half4 _SpecColor;
struct UnityLight
{
	half3 color;
	half3 dir;
	half ndotl;
};
struct UnityIndirect
{
	half3 diffuse;
	half3 specular;
};
struct UnityGI
{
	UnityLight light;
	UnityIndirect indirect;
};
struct UnityGIInput
{
	UnityLight light;
	float3 worldPos;
	half3 worldViewDir;
	half atten;
	half3 ambient;
	float4 lightmapUV;
	float4 boxMin [2];
	float4 boxMax [2];
	float4 probePosition [2];
	float4 probeHDR [2];
};
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityGBuffer.cginc
struct UnityStandardData
{
	half3 diffuseColor;
	half occlusion;
	half3 specularColor;
	half smoothness;
	float3 normalWorld;
};
void UnityStandardDataToGbuffer (UnityStandardData data, out half4 outGBuffer0, out half4 outGBuffer1, out half4 outGBuffer2)
{
	outGBuffer0 = half4 (data . diffuseColor, data . occlusion);
	outGBuffer1 = half4 (data . specularColor, data . smoothness);
	outGBuffer2 = half4 (data . normalWorld * 0.5f + 0.5f, 1.0f);
}
UnityStandardData UnityStandardDataFromGbuffer (half4 inGBuffer0, half4 inGBuffer1, half4 inGBuffer2)
{
	UnityStandardData data;
	data . diffuseColor = inGBuffer0 . rgb;
	data . occlusion = inGBuffer0 . a;
	data . specularColor = inGBuffer1 . rgb;
	data . smoothness = inGBuffer1 . a;
	data . normalWorld = normalize ((float3) inGBuffer2 . rgb * 2 - 1);
	return data;
}
void UnityStandardDataApplyWeightToGbuffer (inout half4 inOutGBuffer0, inout half4 inOutGBuffer1, inout half4 inOutGBuffer2, half alpha)
{
	inOutGBuffer0 . rgb *= alpha;
	inOutGBuffer1 *= alpha;
	inOutGBuffer2 . rgb *= alpha;
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityStandardBRDF.cginc
float PerceptualRoughnessToRoughness (float perceptualRoughness)
{
	return perceptualRoughness * perceptualRoughness;
}
half RoughnessToPerceptualRoughness (half roughness)
{
	return sqrt (roughness);
}
half SmoothnessToRoughness (half smoothness)
{
	return (1 - smoothness) * (1 - smoothness);
}
float SmoothnessToPerceptualRoughness (float smoothness)
{
	return (1 - smoothness);
}
inline half Pow4 (half x)
{
	return x * x * x * x;
}
inline float2 Pow4 (float2 x)
{
	return x * x * x * x;
}
inline half3 Pow4 (half3 x)
{
	return x * x * x * x;
}
inline half4 Pow4 (half4 x)
{
	return x * x * x * x;
}
inline half Pow5 (half x)
{
	return x * x * x * x * x;
}
inline half2 Pow5 (half2 x)
{
	return x * x * x * x * x;
}
inline half3 Pow5 (half3 x)
{
	return x * x * x * x * x;
}
inline half4 Pow5 (half4 x)
{
	return x * x * x * x * x;
}
inline half3 FresnelTerm (half3 F0, half cosA)
{
	half t = Pow5 (1 - cosA);
	return F0 + (1 - F0) * t;
}
inline half3 FresnelLerp (half3 F0, half3 F90, half cosA)
{
	half t = Pow5 (1 - cosA);
	return lerp (F0, F90, t);
}
inline half3 FresnelLerpFast (half3 F0, half3 F90, half cosA)
{
	half t = Pow4 (1 - cosA);
	return lerp (F0, F90, t);
}
half DisneyDiffuse (half NdotV, half NdotL, half LdotH, half perceptualRoughness)
{
	half fd90 = 0.5 + 2 * LdotH * LdotH * perceptualRoughness;
	half lightScatter = (1 + (fd90 - 1) * Pow5 (1 - NdotL));
	half viewScatter = (1 + (fd90 - 1) * Pow5 (1 - NdotV));
	return lightScatter * viewScatter;
}
inline half SmithVisibilityTerm (half NdotL, half NdotV, half k)
{
	half gL = NdotL * (1 - k) + k;
	half gV = NdotV * (1 - k) + k;
	return 1.0 / (gL * gV + 1e-5f);
}
inline half SmithBeckmannVisibilityTerm (half NdotL, half NdotV, half roughness)
{
	half c = 0.797884560802865h;
	half k = roughness * c;
	return SmithVisibilityTerm (NdotL, NdotV, k) * 0.25f;
}
inline float SmithJointGGXVisibilityTerm (float NdotL, float NdotV, float roughness)
{
	float a = roughness;
	float lambdaV = NdotL * (NdotV * (1 - a) + a);
	float lambdaL = NdotV * (NdotL * (1 - a) + a);
	return 0.5f / (lambdaV + lambdaL + 1e-5f);
}
inline float GGXTerm (float NdotH, float roughness)
{
	float a2 = roughness * roughness;
	float d = (NdotH * a2 - NdotH) * NdotH + 1.0f;
	return 0.31830988618f * a2 / (d * d + 1e-7f);
}
inline half PerceptualRoughnessToSpecPower (half perceptualRoughness)
{
	half m = PerceptualRoughnessToRoughness (perceptualRoughness);
	half sq = max (1e-4f, m * m);
	half n = (2.0 / sq) - 2.0;
	n = max (n, 1e-4f);
	return n;
}
inline half NDFBlinnPhongNormalizedTerm (half NdotH, half n)
{
	half normTerm = (n + 2.0) * (0.5 / 3.14159265359f);
	half specTerm = pow (NdotH, n);
	return specTerm * normTerm;
}
inline float3 Unity_SafeNormalize (float3 inVec)
{
	float dp3 = max (0.001f, dot (inVec, inVec));
	return inVec * rsqrt (dp3);
}
half4 BRDF1_Unity_PBS (half3 diffColor, half3 specColor, half oneMinusReflectivity, half smoothness,
float3 normal, float3 viewDir,
UnityLight light, UnityIndirect gi)
{
	float perceptualRoughness = SmoothnessToPerceptualRoughness (smoothness);
	float3 halfDir = Unity_SafeNormalize (float3 (light . dir) + viewDir);
	half nv = abs (dot (normal, viewDir));
	float nl = saturate (dot (normal, light . dir));
	float nh = saturate (dot (normal, halfDir));
	half lv = saturate (dot (light . dir, viewDir));
	half lh = saturate (dot (light . dir, halfDir));
	half diffuseTerm = DisneyDiffuse (nv, nl, lh, perceptualRoughness) * nl;
	float roughness = PerceptualRoughnessToRoughness (perceptualRoughness);
	roughness = max (roughness, 0.002);
	float V = SmithJointGGXVisibilityTerm (nl, nv, roughness);
	float D = GGXTerm (nh, roughness);
	float specularTerm = V * D * 3.14159265359f;
	specularTerm = max (0, specularTerm * nl);
	half surfaceReduction;
	surfaceReduction = 1.0 / (roughness * roughness + 1.0);
	specularTerm *= any (specColor) ? 1.0 : 0.0;
	half grazingTerm = saturate (smoothness + (1 - oneMinusReflectivity));
	half3 color = diffColor * (gi . diffuse + light . color * diffuseTerm)
	+ specularTerm * light . color * FresnelTerm (specColor, lh)
	+ surfaceReduction * gi . specular * FresnelLerp (specColor, grazingTerm, nv);
	return half4 (color, 1);
}
half4 BRDF2_Unity_PBS (half3 diffColor, half3 specColor, half oneMinusReflectivity, half smoothness,
float3 normal, float3 viewDir,
UnityLight light, UnityIndirect gi)
{
	float3 halfDir = Unity_SafeNormalize (float3 (light . dir) + viewDir);
	half nl = saturate (dot (normal, light . dir));
	float nh = saturate (dot (normal, halfDir));
	half nv = saturate (dot (normal, viewDir));
	float lh = saturate (dot (light . dir, halfDir));
	half perceptualRoughness = SmoothnessToPerceptualRoughness (smoothness);
	half roughness = PerceptualRoughnessToRoughness (perceptualRoughness);
	float a = roughness;
	float a2 = a * a;
	float d = nh * nh * (a2 - 1.f) + 1.00001f;
	float specularTerm = a2 / (max (0.1f, lh * lh) * (roughness + 0.5f) * (d * d) * 4);
	half surfaceReduction = (0.6 - 0.08 * perceptualRoughness);
	surfaceReduction = 1.0 - roughness * perceptualRoughness * surfaceReduction;
	half grazingTerm = saturate (smoothness + (1 - oneMinusReflectivity));
	half3 color = (diffColor + specularTerm * specColor) * light . color * nl
	+ gi . diffuse * diffColor
	+ surfaceReduction * gi . specular * FresnelLerpFast (specColor, grazingTerm, nv);
	return half4 (color, 1);
}
sampler2D unity_NHxRoughness;
half3 BRDF3_Direct (half3 diffColor, half3 specColor, half rlPow4, half smoothness)
{
	half LUT_RANGE = 16.0;
	half specular = tex2D (unity_NHxRoughness, half2 (rlPow4, SmoothnessToPerceptualRoughness (smoothness))) . r * LUT_RANGE;
	return diffColor + specular * specColor;
}
half3 BRDF3_Indirect (half3 diffColor, half3 specColor, UnityIndirect indirect, half grazingTerm, half fresnelTerm)
{
	half3 c = indirect . diffuse * diffColor;
	c += indirect . specular * lerp (specColor, grazingTerm, fresnelTerm);
	return c;
}
half4 BRDF3_Unity_PBS (half3 diffColor, half3 specColor, half oneMinusReflectivity, half smoothness,
float3 normal, float3 viewDir,
UnityLight light, UnityIndirect gi)
{
	float3 reflDir = reflect (viewDir, normal);
	half nl = saturate (dot (normal, light . dir));
	half nv = saturate (dot (normal, viewDir));
	half2 rlPow4AndFresnelTerm = Pow4 (float2 (dot (reflDir, light . dir), 1 - nv));
	half rlPow4 = rlPow4AndFresnelTerm . x;
	half fresnelTerm = rlPow4AndFresnelTerm . y;
	half grazingTerm = saturate (smoothness + (1 - oneMinusReflectivity));
	half3 color = BRDF3_Direct (diffColor, specColor, rlPow4, smoothness);
	color *= light . color * nl;
	color += BRDF3_Indirect (diffColor, specColor, gi, grazingTerm, fresnelTerm);
	return half4 (color, 1);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityDeprecated.cginc
inline half3 LazarovFresnelTerm (half3 F0, half roughness, half cosA)
{
	half t = Pow5 (1 - cosA);
	t /= 4 - 3 * roughness;
	return F0 + (1 - F0) * t;
}
inline half3 SebLagardeFresnelTerm (half3 F0, half roughness, half cosA)
{
	half t = Pow5 (1 - cosA);
	return F0 + (max (F0, roughness) - F0) * t;
}
inline half CookTorranceVisibilityTerm (half NdotL, half NdotV, half NdotH, half VdotH)
{
	VdotH += 1e-5f;
	half G = min (1.0, min (
	(2.0 * NdotH * NdotV) / VdotH,
	(2.0 * NdotH * NdotL) / VdotH));
	return G / (NdotL * NdotV + 1e-4f);
}
inline half KelemenVisibilityTerm (half LdotH)
{
	return 1.0 / (LdotH * LdotH);
}
inline half ModifiedKelemenVisibilityTerm (half LdotH, half perceptualRoughness)
{
	half c = 0.797884560802865h;
	half k = PerceptualRoughnessToRoughness (perceptualRoughness) * c;
	half gH = LdotH * (1 - k) + k;
	return 1.0 / (gH * gH);
}
inline half SmithGGXVisibilityTerm (half NdotL, half NdotV, half perceptualRoughness)
{
	half k = (PerceptualRoughnessToRoughness (perceptualRoughness)) / 2;
	return SmithVisibilityTerm (NdotL, NdotV, k);
}
inline half ImplicitVisibilityTerm ()
{
	return 1;
}
inline half RDFBlinnPhongNormalizedTerm (half NdotH, half n)
{
	half normTerm = (n + 2.0) / (8.0 * 3.14159265359f);
	half specTerm = pow (NdotH, n);
	return specTerm * normTerm;
}
inline half3 DecodeHDR_NoLinearSupportInSM2 (half4 data, half4 decodeInstructions)
{
	return DecodeHDR (data, decodeInstructions);
}
inline half DotClamped (half3 a, half3 b)
{
	return max (0.0h, dot (a, b));
}
inline half LambertTerm (half3 normal, half3 lightDir)
{
	return DotClamped (normal, lightDir);
}
inline half BlinnTerm (half3 normal, half3 halfDir)
{
	return DotClamped (normal, halfDir);
}
half RoughnessToSpecPower (half roughness)
{
	return PerceptualRoughnessToSpecPower (roughness);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityImageBasedLighting.cginc
struct Unity_GlossyEnvironmentData
{
	half roughness;
	half3 reflUVW;
};
Unity_GlossyEnvironmentData UnityGlossyEnvironmentSetup (half Smoothness, half3 worldViewDir, half3 Normal, half3 fresnel0)
{
	Unity_GlossyEnvironmentData g;
	g . roughness = SmoothnessToPerceptualRoughness (Smoothness);
	g . reflUVW = reflect (- worldViewDir, Normal);
	return g;
}
half perceptualRoughnessToMipmapLevel (half perceptualRoughness)
{
	return perceptualRoughness * (6);
}
half mipmapLevelToPerceptualRoughness (half mipmapLevel)
{
	return mipmapLevel / (6);
}
half3 Unity_GlossyEnvironment (TextureCube tex, SamplerState samplertex, half4 hdr, Unity_GlossyEnvironmentData glossIn)
{
	half perceptualRoughness = glossIn . roughness;
	perceptualRoughness = perceptualRoughness * (1.7 - 0.7 * perceptualRoughness);
	half mip = perceptualRoughnessToMipmapLevel (perceptualRoughness);
	half3 R = glossIn . reflUVW;
	half4 rgbm = tex . SampleLevel (samplertex, R, mip);
	return DecodeHDR (rgbm, hdr);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityDeprecated.cginc
half3 Unity_GlossyEnvironment (TextureCube tex, SamplerState samplertex, half4 hdr, half3 worldNormal, half perceptualRoughness)
{
	Unity_GlossyEnvironmentData g;
	g . roughness = perceptualRoughness;
	g . reflUVW = worldNormal;
	return Unity_GlossyEnvironment (tex, samplertex, hdr, g);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityStandardUtils.cginc
half SpecularStrength (half3 specular)
{
	return max (max (specular . r, specular . g), specular . b);
}
inline half3 EnergyConservationBetweenDiffuseAndSpecular (half3 albedo, half3 specColor, out half oneMinusReflectivity)
{
	oneMinusReflectivity = 1 - SpecularStrength (specColor);
	return albedo * oneMinusReflectivity;
}
inline half OneMinusReflectivityFromMetallic (half metallic)
{
	half oneMinusDielectricSpec = half4 (0.04, 0.04, 0.04, 1.0 - 0.04) . a;
	return oneMinusDielectricSpec - metallic * oneMinusDielectricSpec;
}
inline half3 DiffuseAndSpecularFromMetallic (half3 albedo, half metallic, out half3 specColor, out half oneMinusReflectivity)
{
	specColor = lerp (half4 (0.04, 0.04, 0.04, 1.0 - 0.04) . rgb, albedo, metallic);
	oneMinusReflectivity = OneMinusReflectivityFromMetallic (metallic);
	return albedo * oneMinusReflectivity;
}
inline half3 PreMultiplyAlpha (half3 diffColor, half alpha, half oneMinusReflectivity, out half outModifiedAlpha)
{
	outModifiedAlpha = alpha;
	return diffColor;
}
half2 ParallaxOffset1Step (half h, half height, half3 viewDir)
{
	h = h * height - height / 2.0;
	half3 v = normalize (viewDir);
	v . z += 0.42;
	return h * (v . xy / v . z);
}
half LerpOneTo (half b, half t)
{
	half oneMinusT = 1 - t;
	return oneMinusT + b * t;
}
half3 LerpWhiteTo (half3 b, half t)
{
	half oneMinusT = 1 - t;
	return half3 (oneMinusT, oneMinusT, oneMinusT) + b * t;
}
half3 UnpackScaleNormalDXT5nm (half4 packednormal, half bumpScale)
{
	half3 normal;
	normal . xy = (packednormal . wy * 2 - 1);
	normal . xy *= bumpScale;
	normal . z = sqrt (1.0 - saturate (dot (normal . xy, normal . xy)));
	return normal;
}
half3 UnpackScaleNormalRGorAG (half4 packednormal, half bumpScale)
{
	packednormal . x *= packednormal . w;
	half3 normal;
	normal . xy = (packednormal . xy * 2 - 1);
	normal . xy *= bumpScale;
	normal . z = sqrt (1.0 - saturate (dot (normal . xy, normal . xy)));
	return normal;
}
half3 UnpackScaleNormal (half4 packednormal, half bumpScale)
{
	return UnpackScaleNormalRGorAG (packednormal, bumpScale);
}
half3 BlendNormals (half3 n1, half3 n2)
{
	return normalize (half3 (n1 . xy + n2 . xy, n1 . z * n2 . z));
}
half3x3 CreateTangentToWorldPerVertex (half3 normal, half3 tangent, half tangentSign)
{
	half sign = tangentSign * unity_WorldTransformParams . w;
	half3 binormal = cross (normal, tangent) * sign;
	return half3x3 (tangent, binormal, normal);
}
half3 ShadeSHPerVertex (half3 normal, half3 ambient)
{
	ambient += SHEvalLinearL2 (half4 (normal, 1.0));
	return ambient;
}
half3 ShadeSHPerPixel (half3 normal, half3 ambient, float3 worldPos)
{
	half3 ambient_contrib = 0.0;
	if (unity_ProbeVolumeParams . x == 1.0)
	ambient_contrib = SHEvalLinearL0L1_SampleProbeVolume (half4 (normal, 1.0), worldPos);
	else
	ambient_contrib = SHEvalLinearL0L1 (half4 (normal, 1.0));
	ambient = max (half3 (0, 0, 0), ambient + ambient_contrib);
	return ambient;
}
inline float3 BoxProjectedCubemapDirection (float3 worldRefl, float3 worldPos, float4 cubemapCenter, float4 boxMin, float4 boxMax)
{
	[branch]
	if (cubemapCenter . w > 0.0)
	{
		float3 nrdir = normalize (worldRefl);
		float3 rbmax = (boxMax . xyz - worldPos) / nrdir;
		float3 rbmin = (boxMin . xyz - worldPos) / nrdir;
		float3 rbminmax = (nrdir > 0.0f) ? rbmax : rbmin;
		float fa = min (min (rbminmax . x, rbminmax . y), rbminmax . z);
		worldPos -= cubemapCenter . xyz;
		worldRefl = worldPos + nrdir * fa;
	}
	return worldRefl;
}
half3 CalculateSurfaceGradient (half3 n, half3 dpdx, half3 dpdy, half dhdx, half dhdy)
{
	half3 r1 = cross (dpdy, n);
	half3 r2 = cross (n, dpdx);
	return (r1 * dhdx + r2 * dhdy) / dot (dpdx, r1);
}
half3 PerturbNormal (half3 n, half3 dpdx, half3 dpdy, half dhdx, half dhdy)
{
	return normalize (n - CalculateSurfaceGradient (n, dpdx, dpdy, dhdx, dhdy));
}
half3 CalculateSurfaceNormal (half3 position, half3 normal, half2 gradient, half2 uv)
{
	half3 dpdx = ddx (position);
	half3 dpdy = ddy (position);
	half dhdx = dot (gradient, ddx (uv));
	half dhdy = dot (gradient, ddy (uv));
	return PerturbNormal (normal, dpdx, dpdy, dhdx, dhdy);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityShadowLibrary.cginc
half UnitySampleShadowmap_PCF7x7 (float4 coord, float3 receiverPlaneDepthBias);
half UnitySampleShadowmap_PCF5x5 (float4 coord, float3 receiverPlaneDepthBias);
half UnitySampleShadowmap_PCF3x3 (float4 coord, float3 receiverPlaneDepthBias);
float3 UnityGetReceiverPlaneDepthBias (float3 shadowCoord, float biasbiasMultiply);
half4 LPPV_SampleProbeOcclusion (float3 worldPos)
{
	const float transformToLocal = unity_ProbeVolumeParams . y;
	const float texelSizeX = unity_ProbeVolumeParams . z;
	float3 position = (transformToLocal == 1.0f) ? mul (unity_ProbeVolumeWorldToObject, float4 (worldPos, 1.0)) . xyz : worldPos;
	float3 texCoord = (position - unity_ProbeVolumeMin . xyz) * unity_ProbeVolumeSizeInv . xyz;
	texCoord . x = max (texCoord . x * 0.25f + 0.75f, 0.75f + 0.5f * texelSizeX);
	return unity_ProbeVolumeSH . Sample (samplerunity_ProbeVolumeSH, texCoord);
}
half UnitySampleBakedOcclusion (float2 lightmapUV, float3 worldPos)
{
	half atten = 1.0f;
	half4 rawOcclusionMask = atten . xxxx;
	if (unity_ProbeVolumeParams . x == 1.0)
	rawOcclusionMask = LPPV_SampleProbeOcclusion (worldPos);
	return saturate (dot (rawOcclusionMask, unity_OcclusionMaskSelector));
	return atten;
}
half4 UnityGetRawBakedOcclusions (float2 lightmapUV, float3 worldPos)
{
	return half4 (1.0, 1.0, 1.0, 1.0);
}
half UnityMixRealtimeAndBakedShadows (half realtimeShadowAttenuation, half bakedShadowAttenuation, half fade)
{
	return bakedShadowAttenuation;
	return lerp (realtimeShadowAttenuation, bakedShadowAttenuation, fade);
}
float UnityComputeShadowFadeDistance (float3 wpos, float z)
{
	float sphereDist = distance (wpos, unity_ShadowFadeCenterAndType . xyz);
	return lerp (z, sphereDist, unity_ShadowFadeCenterAndType . w);
}
half UnityComputeShadowFade (float fadeDist)
{
	return saturate (fadeDist * _LightShadowData . z + _LightShadowData . w);
}
float3 UnityGetReceiverPlaneDepthBias (float3 shadowCoord, float biasMultiply)
{
	float3 biasUVZ = 0;
	return biasUVZ;
}
float3 UnityCombineShadowcoordComponents (float2 baseUV, float2 deltaUV, float depth, float3 receiverPlaneDepthBias)
{
	float3 uv = float3 (baseUV + deltaUV, depth + receiverPlaneDepthBias . z);
	uv . z += dot (deltaUV, receiverPlaneDepthBias . xy);
	return uv;
}
float _UnityInternalGetAreaAboveFirstTexelUnderAIsocelesRectangleTriangle (float triangleHeight)
{
	return triangleHeight - 0.5;
}
void _UnityInternalGetAreaPerTexel_3TexelsWideTriangleFilter (float offset, out float4 computedArea, out float4 computedAreaUncut)
{
	float offset01SquaredHalved = (offset + 0.5) * (offset + 0.5) * 0.5;
	computedAreaUncut . x = computedArea . x = offset01SquaredHalved - offset;
	computedAreaUncut . w = computedArea . w = offset01SquaredHalved;
	computedAreaUncut . y = _UnityInternalGetAreaAboveFirstTexelUnderAIsocelesRectangleTriangle (1.5 - offset);
	float clampedOffsetLeft = min (offset, 0);
	float areaOfSmallLeftTriangle = clampedOffsetLeft * clampedOffsetLeft;
	computedArea . y = computedAreaUncut . y - areaOfSmallLeftTriangle;
	computedAreaUncut . z = _UnityInternalGetAreaAboveFirstTexelUnderAIsocelesRectangleTriangle (1.5 + offset);
	float clampedOffsetRight = max (offset, 0);
	float areaOfSmallRightTriangle = clampedOffsetRight * clampedOffsetRight;
	computedArea . z = computedAreaUncut . z - areaOfSmallRightTriangle;
}
void _UnityInternalGetWeightPerTexel_3TexelsWideTriangleFilter (float offset, out float4 computedWeight)
{
	float4 dummy;
	_UnityInternalGetAreaPerTexel_3TexelsWideTriangleFilter (offset, computedWeight, dummy);
	computedWeight *= 0.44444;
}
void _UnityInternalGetWeightPerTexel_5TexelsWideTriangleFilter (float offset, out float3 texelsWeightsA, out float3 texelsWeightsB)
{
	float4 computedArea_From3texelTriangle;
	float4 computedAreaUncut_From3texelTriangle;
	_UnityInternalGetAreaPerTexel_3TexelsWideTriangleFilter (offset, computedArea_From3texelTriangle, computedAreaUncut_From3texelTriangle);
	texelsWeightsA . x = 0.16 * (computedArea_From3texelTriangle . x);
	texelsWeightsA . y = 0.16 * (computedAreaUncut_From3texelTriangle . y);
	texelsWeightsA . z = 0.16 * (computedArea_From3texelTriangle . y + 1);
	texelsWeightsB . x = 0.16 * (computedArea_From3texelTriangle . z + 1);
	texelsWeightsB . y = 0.16 * (computedAreaUncut_From3texelTriangle . z);
	texelsWeightsB . z = 0.16 * (computedArea_From3texelTriangle . w);
}
void _UnityInternalGetWeightPerTexel_7TexelsWideTriangleFilter (float offset, out float4 texelsWeightsA, out float4 texelsWeightsB)
{
	float4 computedArea_From3texelTriangle;
	float4 computedAreaUncut_From3texelTriangle;
	_UnityInternalGetAreaPerTexel_3TexelsWideTriangleFilter (offset, computedArea_From3texelTriangle, computedAreaUncut_From3texelTriangle);
	texelsWeightsA . x = 0.081632 * (computedArea_From3texelTriangle . x);
	texelsWeightsA . y = 0.081632 * (computedAreaUncut_From3texelTriangle . y);
	texelsWeightsA . z = 0.081632 * (computedAreaUncut_From3texelTriangle . y + 1);
	texelsWeightsA . w = 0.081632 * (computedArea_From3texelTriangle . y + 2);
	texelsWeightsB . x = 0.081632 * (computedArea_From3texelTriangle . z + 2);
	texelsWeightsB . y = 0.081632 * (computedAreaUncut_From3texelTriangle . z + 1);
	texelsWeightsB . z = 0.081632 * (computedAreaUncut_From3texelTriangle . z);
	texelsWeightsB . w = 0.081632 * (computedArea_From3texelTriangle . w);
}
half UnitySampleShadowmap_PCF3x3NoHardwareSupport (float4 coord, float3 receiverPlaneDepthBias)
{
	half shadow = 1;
	return shadow;
}
half UnitySampleShadowmap_PCF3x3Tent (float4 coord, float3 receiverPlaneDepthBias)
{
	half shadow = 1;
	return shadow;
}
half UnitySampleShadowmap_PCF5x5Tent (float4 coord, float3 receiverPlaneDepthBias)
{
	half shadow = 1;
	return shadow;
}
half UnitySampleShadowmap_PCF7x7Tent (float4 coord, float3 receiverPlaneDepthBias)
{
	half shadow = 1;
	return shadow;
}
half UnitySampleShadowmap_PCF3x3Gaussian (float4 coord, float3 receiverPlaneDepthBias)
{
	half shadow = 1;
	return shadow;
}
half UnitySampleShadowmap_PCF5x5Gaussian (float4 coord, float3 receiverPlaneDepthBias)
{
	half shadow = 1;
	return shadow;
}
half UnitySampleShadowmap_PCF3x3 (float4 coord, float3 receiverPlaneDepthBias)
{
	return UnitySampleShadowmap_PCF3x3Tent (coord, receiverPlaneDepthBias);
}
half UnitySampleShadowmap_PCF5x5 (float4 coord, float3 receiverPlaneDepthBias)
{
	return UnitySampleShadowmap_PCF5x5Tent (coord, receiverPlaneDepthBias);
}
half UnitySampleShadowmap_PCF7x7 (float4 coord, float3 receiverPlaneDepthBias)
{
	return UnitySampleShadowmap_PCF7x7Tent (coord, receiverPlaneDepthBias);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/UnityGlobalIllumination.cginc
inline half3 DecodeDirectionalSpecularLightmap (half3 color, half4 dirTex, half3 normalWorld, bool isRealtimeLightmap, half4 realtimeNormalTex, out UnityLight o_light)
{
	o_light . color = color;
	o_light . dir = dirTex . xyz * 2 - 1;
	o_light . ndotl = 0;
	half directionality = max (0.001, length (o_light . dir));
	o_light . dir /= directionality;
	half3 ambient = o_light . color * (1 - directionality);
	o_light . color = o_light . color * directionality;
	ambient *= saturate (dot (normalWorld, o_light . dir));
	return ambient;
}
inline void ResetUnityLight (out UnityLight outLight)
{
	outLight . color = half3 (0, 0, 0);
	outLight . dir = half3 (0, 1, 0);
	outLight . ndotl = 0;
}
inline half3 SubtractMainLightWithRealtimeAttenuationFromLightmap (half3 lightmap, half attenuation, half4 bakedColorTex, half3 normalWorld)
{
	half3 shadowColor = unity_ShadowColor . rgb;
	half shadowStrength = _LightShadowData . x;
	half ndotl = LambertTerm (normalWorld, _WorldSpaceLightPos0 . xyz);
	half3 estimatedLightContributionMaskedByInverseOfShadow = ndotl * (1 - attenuation) * _LightColor0 . rgb;
	half3 subtractedLightmap = lightmap - estimatedLightContributionMaskedByInverseOfShadow;
	half3 realtimeShadow = max (subtractedLightmap, shadowColor);
	realtimeShadow = lerp (realtimeShadow, lightmap, shadowStrength);
	return min (lightmap, realtimeShadow);
}
inline void ResetUnityGI (out UnityGI outGI)
{
	ResetUnityLight (outGI . light);
	outGI . indirect . diffuse = 0;
	outGI . indirect . specular = 0;
}
inline UnityGI UnityGI_Base (UnityGIInput data, half occlusion, half3 normalWorld)
{
	UnityGI o_gi;
	ResetUnityGI (o_gi);
	o_gi . light = data . light;
	o_gi . light . color *= data . atten;
	o_gi . indirect . diffuse *= occlusion;
	return o_gi;
}
inline half3 UnityGI_IndirectSpecular (UnityGIInput data, half occlusion, Unity_GlossyEnvironmentData glossIn)
{
	half3 specular;
	half3 originalReflUVW = glossIn . reflUVW;
	glossIn . reflUVW = BoxProjectedCubemapDirection (originalReflUVW, data . worldPos, data . probePosition [0], data . boxMin [0], data . boxMax [0]);
	half3 env0 = Unity_GlossyEnvironment (unity_SpecCube0, samplerunity_SpecCube0, data . probeHDR [0], glossIn);
	const float kBlendFactor = 0.99999;
	float blendLerp = data . boxMin [0] . w;
	[branch]
	if (blendLerp < kBlendFactor)
	{
		glossIn . reflUVW = BoxProjectedCubemapDirection (originalReflUVW, data . worldPos, data . probePosition [1], data . boxMin [1], data . boxMax [1]);
		half3 env1 = Unity_GlossyEnvironment (unity_SpecCube1, samplerunity_SpecCube0, data . probeHDR [1], glossIn);
		specular = lerp (env1, env0, blendLerp);
	}
	else
	{
		specular = env0;
	}
	return specular * occlusion;
}
inline half3 UnityGI_IndirectSpecular (UnityGIInput data, half occlusion, half3 normalWorld, Unity_GlossyEnvironmentData glossIn)
{
	return UnityGI_IndirectSpecular (data, occlusion, glossIn);
}
inline UnityGI UnityGlobalIllumination (UnityGIInput data, half occlusion, half3 normalWorld)
{
	return UnityGI_Base (data, occlusion, normalWorld);
}
inline UnityGI UnityGlobalIllumination (UnityGIInput data, half occlusion, half3 normalWorld, Unity_GlossyEnvironmentData glossIn)
{
	UnityGI o_gi = UnityGI_Base (data, occlusion, normalWorld);
	o_gi . indirect . specular = UnityGI_IndirectSpecular (data, occlusion, glossIn);
	return o_gi;
}
inline UnityGI UnityGlobalIllumination (UnityGIInput data, half occlusion, half smoothness, half3 normalWorld, bool reflections)
{
	if (reflections)
	{
		Unity_GlossyEnvironmentData g = UnityGlossyEnvironmentSetup (smoothness, data . worldViewDir, normalWorld, float3 (0, 0, 0));
		return UnityGlobalIllumination (data, occlusion, normalWorld, g);
	}
	else
	{
		return UnityGlobalIllumination (data, occlusion, normalWorld);
	}
}
inline UnityGI UnityGlobalIllumination (UnityGIInput data, half occlusion, half smoothness, half3 normalWorld)
{
	bool sampleReflections = true;
	return UnityGlobalIllumination (data, occlusion, smoothness, normalWorld, sampleReflections);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/Lighting.cginc
struct SurfaceOutput {
	half3 Albedo;
	half3 Normal;
	half3 Emission;
	half Specular;
	half Gloss;
	half Alpha;
};
inline half4 UnityLambertLight (SurfaceOutput s, UnityLight light)
{
	half diff = max (0, dot (s . Normal, light . dir));
	half4 c;
	c . rgb = s . Albedo * light . color * diff;
	c . a = s . Alpha;
	return c;
}
inline half4 LightingLambert (SurfaceOutput s, UnityGI gi)
{
	half4 c;
	c = UnityLambertLight (s, gi . light);
	c . rgb += s . Albedo * gi . indirect . diffuse;
	return c;
}
inline half4 LightingLambert_Deferred (SurfaceOutput s, UnityGI gi, out half4 outGBuffer0, out half4 outGBuffer1, out half4 outGBuffer2)
{
	UnityStandardData data;
	data . diffuseColor = s . Albedo;
	data . occlusion = 1;
	data . specularColor = 0;
	data . smoothness = 0;
	data . normalWorld = s . Normal;
	UnityStandardDataToGbuffer (data, outGBuffer0, outGBuffer1, outGBuffer2);
	half4 emission = half4 (s . Emission, 1);
	emission . rgb += s . Albedo * gi . indirect . diffuse;
	return emission;
}
inline void LightingLambert_GI (
SurfaceOutput s,
UnityGIInput data,
inout UnityGI gi)
{
	gi = UnityGlobalIllumination (data, 1.0, s . Normal);
}
inline half4 UnityBlinnPhongLight (SurfaceOutput s, half3 viewDir, UnityLight light)
{
	half3 h = normalize (light . dir + viewDir);
	half diff = max (0, dot (s . Normal, light . dir));
	float nh = max (0, dot (s . Normal, h));
	float spec = pow (nh, s . Specular * 128.0) * s . Gloss;
	half4 c;
	c . rgb = s . Albedo * light . color * diff + light . color * _SpecColor . rgb * spec;
	c . a = s . Alpha;
	return c;
}
inline half4 LightingBlinnPhong (SurfaceOutput s, half3 viewDir, UnityGI gi)
{
	half4 c;
	c = UnityBlinnPhongLight (s, viewDir, gi . light);
	c . rgb += s . Albedo * gi . indirect . diffuse;
	return c;
}
inline half4 LightingBlinnPhong_Deferred (SurfaceOutput s, half3 viewDir, UnityGI gi, out half4 outGBuffer0, out half4 outGBuffer1, out half4 outGBuffer2)
{
	UnityStandardData data;
	data . diffuseColor = s . Albedo;
	data . occlusion = 1;
	data . specularColor = _SpecColor . rgb * s . Gloss * (1 / 3.14159265359f);
	data . smoothness = s . Specular;
	data . normalWorld = s . Normal;
	UnityStandardDataToGbuffer (data, outGBuffer0, outGBuffer1, outGBuffer2);
	half4 emission = half4 (s . Emission, 1);
	emission . rgb += s . Albedo * gi . indirect . diffuse;
	return emission;
}
inline void LightingBlinnPhong_GI (
SurfaceOutput s,
UnityGIInput data,
inout UnityGI gi)
{
	gi = UnityGlobalIllumination (data, 1.0, s . Normal);
}
struct UnityTessellationFactors {
	float edge [3] : SV_TessFactor;
	float inside : SV_InsideTessFactor;
};
half3 DirLightmapDiffuse (in half3x3 dirBasis, half4 color, half4 scale, half3 normal, bool surfFuncWritesNormal, out half3 scalePerBasisVector)
{
	scalePerBasisVector = 1;
	return DecodeLightmap (color);
}
// File: H:/MGFR/Editor/Data/Resources/CGIncludes/AutoLight.cginc
half UnityComputeForwardShadows (float2 lightmapUV, float3 worldPos, float4 screenPos)
{
	float zDist = dot (unity_StereoWorldSpaceCameraPos [unity_StereoEyeIndex] - worldPos, unity_StereoMatrixV [unity_StereoEyeIndex] [2] . xyz);
	float fadeDist = UnityComputeShadowFadeDistance (worldPos, zDist);
	half realtimeToBakedShadowFade = UnityComputeShadowFade (fadeDist);
	half shadowMaskAttenuation = UnitySampleBakedOcclusion (lightmapUV, worldPos);
	half realtimeShadowAttenuation = 1.0f;
	return UnityMixRealtimeAndBakedShadows (realtimeShadowAttenuation, shadowMaskAttenuation, realtimeToBakedShadowFade);
}
// File: Assets/MGFR/Shaders/MgfrCharacter.shader
sampler2D _MainTex;
float4 _MainTex_ST;
half4 _Color;
half4 _SpecTint;
float _Glossiness;
half4 _AmbientColor;
struct appdata
{
	float4 vertex : POSITION;
	float3 normal : NORMAL;
	float2 uv : TEXCOORD0;
	uint instanceID : SV_InstanceID;
};
struct v2f
{
	float4 pos : SV_POSITION;
	float2 uv : TEXCOORD0;
	float3 worldNormal : TEXCOORD1;
	float3 worldPos : TEXCOORD2;
	uint stereoTargetEyeIndex : SV_RenderTargetArrayIndex;
};
v2f vert (appdata v)
{
	v2f o;
	{UnitySetupInstanceID (v . instanceID); UnitySetupCompoundMatrices ();};
	o = (v2f) 0;;
	o . stereoTargetEyeIndex = unity_StereoEyeIndex;
	o . pos = UnityObjectToClipPos (v . vertex);
	o . uv = (v . uv . xy * _MainTex_ST . xy + _MainTex_ST . zw);
	o . worldNormal = UnityObjectToWorldNormal (v . normal);
	o . worldPos = mul (unity_ObjectToWorld, v . vertex) . xyz;
	;
	return o;
}
half4 frag (v2f i) : COLOR
{
	unity_StereoEyeIndex = i . stereoTargetEyeIndex;;
	half4 tex = tex2D (_MainTex, i . uv);
	half4 c = tex * _Color;
	float3 n = normalize (i . worldNormal);
	float3 l = normalize (_WorldSpaceLightPos0 . xyz);
	float ndl = abs (dot (n, l));
	half atten = UnityComputeForwardShadows (0, i . worldPos, 0);;
	half3 lit = c . rgb * (ndl * _LightColor0 . rgb * atten + _AmbientColor . rgb);
	float3 viewDir = normalize (unity_StereoWorldSpaceCameraPos [unity_StereoEyeIndex] - i . worldPos);
	float3 h = normalize (l + viewDir);
	float spec = pow (saturate (abs (dot (n, h))), _Glossiness * 64.0 + 1.0);
	lit += _SpecTint . rgb * spec * ndl * atten;
	return half4 (lit, MgfrCoverageAlpha (_MGFRRgbKeyCoverage > .5 ? tex2D (_MainTex, MgfrCoverageUV (i . uv, i . pos . xy)) . a * _Color . a : c . a, i . pos . xy));
}