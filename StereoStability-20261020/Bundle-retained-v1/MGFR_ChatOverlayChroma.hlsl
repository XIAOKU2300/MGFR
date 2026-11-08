// File: Assets/Subtitle/ChatOverlayChroma.shader
static const int INSTANCING_ON = 0;
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
// File: Assets/Subtitle/ChatOverlayChroma.shader
struct appdata {float4 vertex : POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; uint instanceID : SV_InstanceID;};
struct v2f {float4 vertex : SV_POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; uint stereoTargetEyeIndex : SV_RenderTargetArrayIndex;};
sampler2D _MainTex; float _MGFRSubtitleOpaquePanel; float _MGFRRgbKeyCoverage;
v2f vert (appdata v)
{
	v2f o; {UnitySetupInstanceID (v . instanceID); UnitySetupCompoundMatrices ();}; o . stereoTargetEyeIndex = unity_StereoEyeIndex;
	o . vertex = UnityObjectToClipPos (v . vertex); o . uv = v . uv; o . color = v . color; return o;
}
half4 frag (v2f i) : COLOR
{
	unity_StereoEyeIndex = i . stereoTargetEyeIndex;;
	half4 color = i . color; color . a *= tex2D (_MainTex, i . uv) . a;
	if (_MGFRRgbKeyCoverage > .5 && _MGFRSubtitleOpaquePanel > .5) color . a = 1;
	return color;
}