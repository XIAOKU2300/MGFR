Shader "MGFR/ZmdEndfield/Hair"
{
    Properties
    {
        _ZmdExposure("Character exposure",Float)=1
        _ZmdNormalScale("Raw RG normal scale",Float)=1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull",Float)=0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend("Source blend",Float)=1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend("Destination blend",Float)=0
        [Enum(Off,0,On,1)] _ZWrite("Depth write",Float)=1
        [Header(Map)]
        _BaseColor ("Base Color", 2D) = "white" {}
        _Normal ("Normal", 2D) = "bump" {}
        _Mask ("Mask", 2D) = "white" {}
        _HairLine ("HairLine", 2D) = "white" {}
        _Aniso ("Aniso", 2D) = "white" {}
        _OutLineMask ("Outline Mask", 2D) = "white" {}

        [Header(BaseColor)]
        _Color ("Color", Color) = (1, 1, 1, 1)
        _SecondColor ("Second Color", Color) = (1, 1, 1, 1)
        _ShadowColor ("Shadow Color", Color) = (0.5, 0.5, 0.5, 1)
        _TopLightColor ("Top Light Color", Color) = (1, 1, 1, 1)
        _ShadowStrength ("Shadow Strength", Range(0, 1)) = 0.5
        _DiffuseRamp ("Diffuse Ramp (NPR)", 2D) = "white" {}
        _RampStrength ("NPR Ramp Strength", Range(0, 1)) = 1.0
        _TopLightOffset ("Top Light Offset", Range(-1, 1)) = 0
        _TopLightIntensity ("Top Light Intensity", Range(0, 100)) = 10

        [Header(Normal)]
        _NormalStrength ("Normal Strength", Range(0, 5)) = 1

        [Header(AO)]
        _AO_Offset ("AO Offset", Range(-1, 1)) = 0

        [Header(Specular)]
        _SpecularColor ("Specular Color", Color) = (1, 1, 1, 1)
        _SpecularOffset ("Specular Offset", Range(0, 1)) = 0.5
        _SpecularIntensity ("Specular Intensity", Float) = 1

        [Header(Aniso)]
        _AnisoNoise ("Aniso Noise", Float) = 1
        _AnisoShininess ("Aniso Shininess", Range(0, 1000)) = 400
        _AnisoOffset ("Aniso Offset", Float) = 0
        _AnisoPosition ("Aniso Position", Float) = 0.15
        _CutOffset ("Cut Offset", Float) = 0

        [Header(Env)]
        _EnvSpecularColor ("Env Specular Color", Color) = (1, 1, 1, 1)
        _EnvSpecularIntensity ("Env Specular Intensity", Range(0, 2)) = 0.5
        _EnvSmoothness ("Env Smoothness", Range(0, 1)) = 0.5

        [Header(Transparent)]
        _Alpha ("Alpha", Range(0, 5)) = 1
        _AlphaClip ("Alpha Clip Threshold", Range(0.0, 1.0)) = 0.5
        _DepthAlphaClip ("Depth Prepass Clip Threshold", Range(0.0, 1.0)) = 0.75

        [Header(Outline)]
        _OutLine ("Outline", Float) = 1
        _OutLineColor ("Outline Color", Color) = (1, 1, 1, 1)

        [HideInInspector] _PerObjectShadowEnabled ("Per Object Shadow Enabled", Float) = 1
        [HideInInspector] _StencilRef ("Stencil Ref", Float) = 1
    }
    
    SubShader
    {
        Tags 
        { 
            "RenderType" = "Transparent" 
            "Queue" = "Transparent" 
             
        }

        // ------------------------------------------------------------------
        // Pass 0: Transparency Pass（用于透过半透明头发看到其他头发）
        // ------------------------------------------------------------------

        // ------------------------------------------------------------------
        // Pass 1: Forward Lit (半透明颜色渲染)
        // ------------------------------------------------------------------
        Pass
        {
            Name "ForwardBase"
            Tags { "LightMode" = "ForwardBase" }

            Stencil
            {
                Ref [_StencilRef]
                Comp Always
                Pass Replace
            }

            
            Cull [_Cull] ZWrite [_ZWrite] Blend [_SrcBlend] [_DstBlend]
            HLSLPROGRAM
#pragma target 3.5
#pragma multi_compile_instancing
            #pragma vertex vert
            #pragma fragment frag
            
            
            #pragma multi_compile_fwdbase
            
            #include "ZmdBuiltInCompat.cginc"
            #include "ZmdBuiltInCompat.cginc"
            #include "ZmdBuiltInCompat.cginc"
            #include "ZmdBuiltInCompat.cginc"
            #include "ZmdBuiltInCompat.cginc"
            #include "ZmdBuiltInCompat.cginc"

            struct Attributes
            {
 UNITY_VERTEX_INPUT_INSTANCE_ID
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
            };

            struct Varyings
            {
 UNITY_VERTEX_OUTPUT_STEREO
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 positionWS : TEXCOORD1;
                float3 normalWS : TEXCOORD2;
                float3 tangentWS : TEXCOORD3;
                float3 bitangentWS : TEXCOORD4;
                float4 perObjectShadowCoord : TEXCOORD5;
                float4 shadowCoord : TEXCOORD6;
                float3 positionVS : TEXCOORD7;
                float4 positionNDC : TEXCOORD8;
                float3 positionOS : TEXCOORD9;
                float3 sphereNormalWS : TEXCOORD10;
                float3 sphereBitangentWS : TEXCOORD11;
            };

            TEXTURE2D(_BaseColor);
            SAMPLER(sampler_BaseColor);
            TEXTURE2D(_Normal);
            SAMPLER(sampler_Normal);
            TEXTURE2D(_Mask);
            SAMPLER(sampler_Mask);
            TEXTURE2D(_DiffuseRamp);
            SAMPLER(sampler_DiffuseRamp);
            TEXTURE2D(_HairLine);
            SAMPLER(sampler_HairLine);
            TEXTURE2D(_Aniso);
            SAMPLER(sampler_Aniso);

            CBUFFER_START(UnityPerMaterialHair)
                float4 _BaseColor_ST;
                float4 _Normal_ST;
                float4 _Mask_ST;
                float4 _HairLine_ST;
                float4 _Aniso_ST;
                float4 _Color;
                float4 _TopLightColor;
                float4 _SecondColor;
                float4 _ShadowColor;
                half _ShadowStrength;
                float _RampStrength;
                float4 _SpecularColor;
                float _Alpha;
                float _AlphaClip;
                float _TopLightOffset;
                float _TopLightIntensity;
                float _NormalStrength;
                float _AO_Offset;
                float _SpecularOffset;
                float _SpecularIntensity;
                float _AnisoNoise;
                float _AnisoShininess;
                float _AnisoOffset;
                float _AnisoPosition;
                float _CutOffset;
                float4 _EnvSpecularColor;
                float _EnvSpecularIntensity;
                float _EnvSmoothness;
            CBUFFER_END

            float4 _HeadForward;  
            float4 _HeadPosition; 
            float4 _HeadUp;       

            #define S_CHAR_FORWARD_PASS
            #define S_CHAR_TRANSPARENT
            #include "ZmdCharUtils.cginc"

            Varyings vert(Attributes input)
            {
                Varyings output;
 UNITY_SETUP_INSTANCE_ID(input); UNITY_INITIALIZE_OUTPUT(Varyings,output); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);
                VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = vertexInput.positionCS;
                output.positionWS = vertexInput.positionWS;
                output.uv = TRANSFORM_TEX(input.uv, _BaseColor);
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.tangentWS = TransformObjectToWorldDir(input.tangentOS.xyz);
                output.bitangentWS = cross(output.normalWS, output.tangentWS);
                output.perObjectShadowCoord = ComputeScreenPos(vertexInput.positionCS);
                output.shadowCoord = GetShadowCoord(vertexInput);
                output.positionVS = TransformWorldToView(vertexInput.positionWS);
                output.positionNDC = ComputeScreenPos(vertexInput.positionCS);
                output.positionOS = input.positionOS.xyz;

                // 计算球形法线和副切线 (移动到顶点着色器中 节省性能，同时优化了矩阵乘法)
                float3 sphereNormalWS = normalize(vertexInput.positionWS - (_HeadPosition.xyz + float3(0, _AnisoPosition, 0)));
                float3 cameraRightWS = UNITY_MATRIX_V[0].xyz; // 等价于视图空间的 (1,0,0) 转换到世界空间
                float3 sphereBitangentWS = normalize(cross(sphereNormalWS, cameraRightWS));
                
                output.sphereNormalWS = sphereNormalWS;
                output.sphereBitangentWS = sphereBitangentWS;

                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
 UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                //输入
                half4 baseMap = SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, input.uv);
                half4 normal = SAMPLE_TEXTURE2D(_Normal, sampler_Normal, input.uv);
                half4 maskMap = SAMPLE_TEXTURE2D(_Mask, sampler_Mask, input.uv);
                half hairLine = SAMPLE_TEXTURE2D(_HairLine, sampler_HairLine, input.uv * _HairLine_ST.xy + _HairLine_ST.zw).r;
                half aniso = SAMPLE_TEXTURE2D(_Aniso, sampler_Aniso, input.uv * _Aniso_ST.xy + _Aniso_ST.zw).r;
                half frontHair = 1 - maskMap.r;
                half specMask = maskMap.g;
                half ao = saturate(maskMap.b + _AO_Offset);
                baseMap.rgb = lerp(baseMap.rgb, baseMap.rgb * _SecondColor.rgb, hairLine) * _Color.rgb;
                half alpha = saturate(baseMap.a * _Alpha);
                clip(alpha - _AlphaClip);

                //向量
                half3 normalWS = normalize(input.normalWS);
                half3 tangentWS = normalize(input.tangentWS);
                half3 bitangentWS = normalize(input.bitangentWS);
                half3 viewDirWS = normalize(GetWorldSpaceViewDir(input.positionWS));
                half3 positionOS = input.positionOS;
                positionOS.x += 0.1;
                Light mainLight = GetMainLight(input.shadowCoord);

                //法线
                half3 normalTS_HL;
                normalTS_HL.xy = (normal.ba * 2.0 - 1.0)*half2(1,-1);
                normalTS_HL.z = sqrt(saturate(1.0 - dot(normalTS_HL.xy, normalTS_HL.xy)));

                half3 normalTS;
                normalTS.xy = (normal.rg * 2.0 - 1.0) * half2(1,-1) * _NormalStrength;
                normalTS.z = sqrt(saturate(1.0 - dot(normalTS.xy, normalTS.xy)));

                half3x3 TBN = half3x3(tangentWS, bitangentWS, normalWS);
                half3 normalWS_HL = normalize(mul(normalTS_HL, TBN));
                normalWS = normalize(mul(normalTS, TBN));

                //阴影
                half unityShadow = lerp(1.0, mainLight.shadowAttenuation, _Global_ShadowStrength);
                half3 screenShadow = saturate(SamplePerObjectScreenSpaceShadowmap(input.perObjectShadowCoord));

                half finalShadowStrength = _Global_ShadowStrength * _ShadowStrength;
                half3 coloredShadow = lerp(_ShadowColor.rgb, half3(1.0, 1.0, 1.0), screenShadow.x);
                half3 perObjectShadow = lerp(half3(1.0, 1.0, 1.0), screenShadow, finalShadowStrength) * coloredShadow;
                
                half3 shadowAtten = perObjectShadow;

                //直接光漫反射
                half3 baseColor = baseMap.rgb * _SpecularOffset;
                half NdotL = dot(normalWS, mainLight.direction);
                half halfLambert = min((NdotL * 0.5 + 0.5), unityShadow);
                half3 ramp = SAMPLE_TEXTURE2D(_DiffuseRamp, sampler_DiffuseRamp, half2(halfLambert, 0.5)).rgb;
                half3 baseDiffuse = baseColor * mainLight.color;
                half3 softLightRamp = BlendSoftLight(baseDiffuse, ramp);
                half3 finalDiff = lerp(baseDiffuse, softLightRamp, _RampStrength) * shadowAtten;

                half topNdotL = dot(normalWS, _HeadUp.xyz);
                half topLambert = saturate(topNdotL * 0.5 + 0.5 + _TopLightOffset);
                half3 topLightColor = baseColor * topLambert * _TopLightColor.rgb * _TopLightIntensity * shadowAtten;
                finalDiff += topLightColor;

                //间接光漫反射
                half3 finalEnv = SampleSH(normalWS) * baseColor;

                //直接光镜面反射
                half3 sphereNormalWS = normalize(input.sphereNormalWS);
                half3 sphereBitangentWS = normalize(input.sphereBitangentWS);
                
                half anisoNoise = aniso * 2 - 1;
                sphereNormalWS = lerp(sphereNormalWS, normalWS_HL, 0.25);

                half3 halfDir = normalize(_HeadForward.xyz + viewDirWS);
                half fresnel = max(0, dot(normalWS, viewDirWS));
                fresnel *= fresnel;
                half3 anisoOffset = sphereNormalWS * (anisoNoise * _AnisoNoise + _AnisoOffset);
                half3 binormal = normalize(sphereBitangentWS + anisoOffset);
                half BdotH = dot(binormal, halfDir);
                half specTemp = pow(sqrt(saturate(1.0 - BdotH * BdotH)), _AnisoShininess);

                anisoOffset = sphereNormalWS * (anisoNoise * _AnisoNoise + _AnisoOffset + _CutOffset);
                binormal = normalize(sphereBitangentWS + anisoOffset);
                BdotH = dot(binormal, halfDir);
                half cutSpecTemp = pow(sqrt(saturate(1.0 - BdotH * BdotH)), _AnisoShininess * 2);
                half anisoCut = smoothstep(0, 0.1, cutSpecTemp);

                half3 specColor = baseMap.rgb * (1 - _SpecularOffset) * mainLight.color;
                half3 finalRingSpec = saturate(specTemp - anisoCut) * specColor * _SpecularColor.rgb * (specMask * fresnel) * _SpecularIntensity * screenShadow;

                anisoOffset = normalWS_HL * (anisoNoise * _AnisoNoise + _AnisoOffset);
                binormal = normalize(bitangentWS + anisoOffset);
                BdotH = dot(binormal, halfDir);
                specTemp = pow(sqrt(saturate(1.0 - BdotH * BdotH)), _AnisoShininess);
                half3 finalSpec = specTemp * specColor * _SpecularColor.rgb * specMask * _SpecularIntensity * screenShadow;
                finalSpec = lerp(finalSpec, finalRingSpec, frontHair);

                // 菲涅尔反射
                //间接光镜面反射
                half3 reflectDir = reflect(-viewDirWS, normalWS);
                half3 envMap = GlossyEnvironmentReflection(reflectDir, input.positionWS, _EnvSmoothness, 1.0);
                half3 finalEnvSpec = envMap * specColor * _EnvSpecularColor.rgb * _EnvSpecularIntensity;

                // 调用全局封装的角色边缘光计算
                half3 inner_rim = 0;
                half3 final_rim = 0;
                CalculateAnimeRimLight(normalWS, viewDirWS, NdotL, screenShadow, baseMap.rgb, input.positionVS, input.positionNDC, positionOS, inner_rim, final_rim);

                half3 finalColor = (finalDiff + finalEnv + finalEnvSpec + finalSpec) * ao + final_rim * 1.5;
                return half4(ZmdFinish(finalColor), alpha);
            }
            ENDHLSL
        }
        // ------------------------------------------------------------------
        // Pass 2: Depth Prepass 
        // ------------------------------------------------------------------
        
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            ZWrite On
            ColorMask 0
            Cull Back

            HLSLPROGRAM
#pragma target 3.5
#pragma multi_compile_instancing
            #pragma multi_compile_shadowcaster
            #pragma vertex SChar_ShadowVert
            #pragma fragment SChar_ShadowFrag
            #include "ZmdCharUtils.cginc"
            ENDHLSL
        }

        Pass
        {
            Name "Outline"
            Tags { "LightMode" = "SRPDefaultUnlit" }

            Cull Front

            HLSLPROGRAM
#pragma target 3.5
#pragma multi_compile_instancing
            #pragma vertex SChar_OutlineVert
            #pragma fragment SChar_OutlineFrag
            #include "ZmdCharUtils.cginc"
            ENDHLSL
        }
    }
}