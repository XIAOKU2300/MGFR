Shader "MGFR/ZmdEndfield/Cloth/MrCoverage"
{
    Properties
    {
        _Color("Model material tint",Color)=(1,1,1,1)
        _ZmdExposure("Character exposure",Float)=1
        _ZmdNormalScale("Raw RG normal scale",Float)=1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("Cull",Float)=0
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend("Source blend",Float)=1
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend("Destination blend",Float)=0
        [Enum(Off,0,On,1)] _ZWrite("Depth write",Float)=1
        // =================================================================================
        [Header(Surface Maps)]
        _BaseColor ("Base Color", 2D) = "white" {}
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _MOR ("Metallic(R) Occlusion(B) Roughness(A)", 2D) = "white" {}
        _Emission ("Emission", 2D) = "white" {}
        _DiffuseRamp ("Diffuse Ramp (NPR)", 2D) = "white" {}
        [HideInInspector] _StencilRef("Stencil Ref", Float) = 1

        // =================================================================================
        [Header(Surface Options)]
        _AlphaClip ("Alpha Clip Threshold", Range(0, 1)) = 0.5

        // =================================================================================
        [Header(Base Color)]
        _TintColor ("Tint Color", Color) = (1, 1, 1, 1)
        _ShadowColor ("Shadow Color", Color) = (0.5, 0.5, 0.5, 1)
        _ShadowStrength ("Shadow Strength", Range(0, 1)) = 0.5
        _BaseColor_Contrast ("Base Color Contrast", Range(0.5, 2)) = 1.0
        _RampStrength ("NPR Ramp Strength", Range(0, 1)) = 1.0

        // =================================================================================
        [Header(PBR Properties (Adjustments for MOR Map))]
        _Metallic ("Metallic Adjust", Range(-1, 1)) = 0
        _Metallic_Contrast ("Metallic Contrast", Range(0, 2)) = 1.0
        _Roughness ("Non-Metal Roughness Adjust", Range(-1, 1)) = 0
        _Roughness_Contrast ("Non-Metal Roughness Contrast", Range(0, 2)) = 1.0
        _Roughness_Metal ("Metal Roughness Adjust", Range(-1, 1)) = 0
        _Roughness_Metal_Contrast ("Metal Roughness Contrast", Range(0, 2)) = 1.0
        _AO_Offset ("AO Adjust", range(-1, 1)) = 0
        _AO_Contrast ("AO Contrast", Range(0, 2)) = 1.0

        // =================================================================================
        [Header(Normal Mapping)]
        _NormalStrength ("Normal Strength", Range(0, 2)) = 1.0

        // =================================================================================
        [Header(Specular)]
        _SpecularColor ("Specular Color", Color) = (1, 1, 1, 1)
        _SpecularIntensity ("Specular Intensity", Range(0, 5)) = 1
        _SpecShininese ("Specular Shininess", Range(2, 500)) = 32
        [Space(10)]
        _EnvSpecularColor ("Env Specular Color", Color) = (1, 1, 1, 1)
        _EnvSpecularIntensity ("Env Specular Intensity", Range(0, 2)) = 0.5
        _EnvSmoothness ("Env Smoothness", Range(0, 1)) = 0.5

        // =================================================================================
        [Header(Emission)]
        _EmissionColor ("Emission Color", Color) = (1, 1, 1, 1)
        _EmissionIntensity ("Emission Intensity", Range(0, 5)) = 1

        // =================================================================================
        [Header(Outline)]
        _OutLine ("Outline Width", range(0, 5)) = 1
        _OutLineColor ("Outline Color", Color) = (1, 1, 1, 1)

        // =================================================================================
        [Header(Gradient)]
        _GradientColor ("Gradient Color", Color) = (1, 1, 1, 1)
        _GradientMinY ("Gradient Min Y", Float) = 0.0
        _GradientMaxY ("Gradient Max Y", Float) = 1.0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque"  "Queue"="Geometry" }
        LOD 100

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "ForwardBase" }

            Stencil
            {
                Ref [_StencilRef]
                Comp Always
                Pass Replace
            }
            ZTest LEqual

            
            Cull [_Cull] ZWrite [_ZWrite] Blend [_SrcBlend] [_DstBlend]
            HLSLPROGRAM
#include "Assets/RepairCoverage.cginc"
#pragma target 3.5
#pragma multi_compile_instancing
#pragma multi_compile _ STEREO_INSTANCING_ON
#pragma multi_compile _ MGFR_BUILD_STEREO_VARIANT
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
                float4 uv7 : TEXCOORD7; // 引入 uv7 (平滑法线)
            };

            struct Varyings
            {
 UNITY_VERTEX_OUTPUT_STEREO
                float2 uv : TEXCOORD0;
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD1;
                float3 positionWS : TEXCOORD2;
                float4 perObjectShadowCoord : TEXCOORD3;
                float4 tangentWS : TEXCOORD4; // w: bitangent sign
                float3 positionVS : TEXCOORD5;
                float4 positionNDC : TEXCOORD6;
                float3 smoothNormalWS : TEXCOORD7; // 传递世界空间的平滑法线
                float3 positionOS : TEXCOORD8;
            };

            TEXTURE2D(_BaseColor);
            SAMPLER(sampler_BaseColor);
            TEXTURE2D(_DiffuseRamp);
            SAMPLER(sampler_DiffuseRamp);
            TEXTURE2D(_MOR);
            SAMPLER(sampler_MOR);
            TEXTURE2D(_NormalMap);
            SAMPLER(sampler_NormalMap);
            TEXTURE2D(_Emission);
            SAMPLER(sampler_Emission);

            float _PerObjectShadowEnabled;

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor_ST;
                half4 _Color;
                half4 _TintColor;
                half4 _ShadowColor;
                half _ShadowStrength;
                half _RampStrength;
                half _BaseColor_Contrast;
                half _AlphaClip;
                half _AO_Offset;
                half _AO_Contrast;
                half _NormalStrength;
                half _Metallic;
                half _Metallic_Contrast;
                half _Roughness;
                half _Roughness_Contrast;
                half _Roughness_Metal;
                half _Roughness_Metal_Contrast;
                half4 _SpecularColor;
                half _SpecularIntensity;
                half _SpecShininese;
                half4 _EmissionColor;
                half _EmissionIntensity;
                half4 _EnvSpecularColor;
                half _EnvSpecularIntensity;
                half _EnvSmoothness;
                half4 _GradientColor;
                half _GradientMinY;
                half _GradientMaxY;
            CBUFFER_END

            #define S_CHAR_FORWARD_PASS
            #include "ZmdCharUtils.cginc"

            Varyings vert (Attributes v)
            {
                Varyings o;
 UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_OUTPUT(Varyings,o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                VertexPositionInputs vertexInput = GetVertexPositionInputs(v.positionOS.xyz);
                VertexNormalInputs normalInput = GetVertexNormalInputs(v.normalOS, v.tangentOS);

                o.positionCS = vertexInput.positionCS;
                o.positionWS = vertexInput.positionWS;
                o.positionVS = TransformWorldToView(vertexInput.positionWS);
                o.positionNDC = ComputeScreenPos(vertexInput.positionCS);

                o.normalWS = normalInput.normalWS;
                o.tangentWS = float4(normalInput.tangentWS, v.tangentOS.w);
                
                // 解析 UV7 里的平滑法线
                float3 smoothNormalWS = normalInput.tangentWS * v.uv7.x + normalInput.bitangentWS * v.uv7.y + normalInput.normalWS * v.uv7.z;
                o.smoothNormalWS = normalize(smoothNormalWS);
                
                o.perObjectShadowCoord = ComputeScreenPos(vertexInput.positionCS);
                o.positionOS = v.positionOS.xyz;
                
                o.uv = TRANSFORM_TEX(v.uv, _BaseColor);
                return o;
            }

            half4 frag (Varyings i) : SV_Target
            {
 UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                // 输入
                half2 uv = i.uv;
                half4 baseMap = SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, uv) * _TintColor * _Color;
                half alpha = baseMap.a;
                
                clip(alpha - _AlphaClip);

                half4 MOR = SAMPLE_TEXTURE2D(_MOR, sampler_MOR, uv);
                MOR.a=1-MOR.a; // Si P alpha is smoothness; ZMD MOR alpha is roughness.
                half4 normalMap = SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, uv);
                half4 emission = SAMPLE_TEXTURE2D(_Emission, sampler_Emission, uv);
                half metallic = saturate(MOR.r + _Metallic);
                metallic = saturate((metallic - 0.5) * _Metallic_Contrast + 0.5);
                half ao = saturate(MOR.b + _AO_Offset);
                ao = saturate((ao - 0.5) * _AO_Contrast + 0.5);
                
                half roughness_nonMetal = saturate(MOR.a + _Roughness);
                roughness_nonMetal = saturate((roughness_nonMetal - 0.5) * _Roughness_Contrast + 0.5);
                half roughness_metal = saturate(MOR.a + _Roughness_Metal);
                roughness_metal = saturate((roughness_metal - 0.5) * _Roughness_Metal_Contrast + 0.5);
                half roughness = lerp(roughness_nonMetal, roughness_metal, metallic);

                half3 base_color = lerp(baseMap.rgb, half3(0,0,0), metallic);
                base_color = saturate((base_color - 0.5) * _BaseColor_Contrast + 0.5);
                half3 f0 = half3(0.04, 0.04, 0.04);
                half3 spec_color = lerp(f0, baseMap.rgb, metallic);

                //向量
                half3 normalWS = normalize(i.normalWS);
                half3 tangentWS = normalize(i.tangentWS.xyz);
                half bitangentSign = i.tangentWS.w;
                half3 bitangentWS = cross(normalWS, tangentWS) * bitangentSign;
                half3 normalVS = TransformWorldToViewDir(normalWS, true);
                half3 viewDirWS = normalize(GetWorldSpaceViewDir(i.positionWS));
                float4 mainShadowCoord = TransformWorldToShadowCoord(i.positionWS);
                Light mainLight = GetMainLight(mainShadowCoord);

                // 法线
                half3 normalTS = ZmdUnpackRG(normalMap);
                normalTS.xy *= _NormalStrength;
                normalTS = normalize(normalTS);
                half3x3 TBN = half3x3(tangentWS, bitangentWS, normalWS);
                normalWS = normalize(mul(normalTS, TBN));

                // 阴影
                half unityShadow = lerp(1.0, mainLight.shadowAttenuation, _Global_ShadowStrength);
                half3 screenShadow = saturate(SamplePerObjectScreenSpaceShadowmap(i.perObjectShadowCoord));

                half finalShadowStrength = _Global_ShadowStrength * _ShadowStrength;
                half3 coloredShadow = lerp(_ShadowColor.rgb, half3(1.0, 1.0, 1.0), screenShadow.x);
                half3 perObjectShadow = lerp(half3(1.0, 1.0, 1.0), screenShadow, finalShadowStrength) * coloredShadow;
                
                half3 shadowAtten = perObjectShadow;

                //直接光漫反射
                half NdotL = dot(normalWS, mainLight.direction);
                half halfLambert = NdotL * 0.5 + 0.5;
                half halfLambertShadow = min(halfLambert, unityShadow);
                half3 rampLambert = SAMPLE_TEXTURE2D(_DiffuseRamp, sampler_DiffuseRamp, half2(halfLambert, 0.5)).rgb * halfLambertShadow;
                half3 rampDiffuse = BlendSoftLight(base_color * mainLight.color, rampLambert);
                half3 grayDiffuse = base_color * mainLight.color * halfLambertShadow;
                half3 baseDiffuse = lerp(grayDiffuse, rampDiffuse, _RampStrength);
                half gradient = saturate((i.positionOS.y - _GradientMinY) / (_GradientMaxY - _GradientMinY + 1e-5));
                half3 diffGradient = lerp(baseDiffuse * _GradientColor.rgb, baseDiffuse, gradient);
                half3 final_diff = diffGradient * shadowAtten;

                // 直接光镜面反射
                half3 halfDir = normalize(viewDirWS + mainLight.direction);
                half NdotH = max(0, dot(normalWS, halfDir));
                half VdotH = max(0, dot(viewDirWS, halfDir));
                half smoothness = 1 - roughness;
                half shininess = lerp(1.0, _SpecShininese, smoothness); 
                half energyConservation = (shininess + 2.0) / (8.0 * 3.1415926); 
                
                // Fresnel 效应 (Schlick 近似)
                half3 fresnelTerm = spec_color + (1.0 - spec_color) * pow(1.0 - VdotH, 5.0);
                
                half spec_temp = pow(NdotH, shininess) * energyConservation;
                half3 final_spec = fresnelTerm * mainLight.color * _SpecularColor.rgb * _SpecularIntensity * spec_temp * screenShadow * halfLambert;

                // 间接光漫反射
                half3 ambient = SampleSH(normalWS);
                half3 final_env = ambient * base_color;

                // 间接光镜面反射
                half3 reflectDir = reflect(-viewDirWS, normalWS);
                half NdotV = max(0, dot(normalWS, viewDirWS));
                half envRoughness = lerp(smoothness, 1.0 - _EnvSmoothness, _EnvSmoothness);
                envRoughness = envRoughness * (1.7 - 0.7 * envRoughness);
                half3 envMap = GlossyEnvironmentReflection(reflectDir, i.positionWS, envRoughness, 1.0);
                
                // 间接�?Fresnel 效应 (考虑粗糙度的 Schlick 近似)
                half3 envFresnel = spec_color + (max(smoothness.xxx, spec_color) - spec_color) * pow(1.0 - NdotV, 5.0);
                
                half3 final_env_spec = envMap * envFresnel * _EnvSpecularColor.rgb * _EnvSpecularIntensity * halfLambert;

                //自发光
                half3 final_emi = emission * _EmissionColor * _EmissionIntensity; 

                // 调用全局封装的角色边缘光计算
                half3 inner_rim = 0;
                half3 final_rim = 0;

                // 边缘光
                CalculateAnimeRimLight(normalWS, viewDirWS, NdotL, screenShadow, baseMap.rgb, i.positionVS, i.positionNDC, i.positionOS, inner_rim, final_rim);

                // 混合
                
                half3 finalColor = (final_diff + final_env + final_spec + final_env_spec) * ao + final_emi + final_rim + inner_rim;

                return half4(ZmdFinish(finalColor),MgfrCoverageAlpha(_MGFRRgbKeyCoverage>.5 ? SAMPLE_TEXTURE2D(_BaseColor,sampler_BaseColor,MgfrCoverageUV(i.uv,i.positionCS.xy)).a*_TintColor.a*_Color.a : alpha,i.positionCS.xy));
            }
            ENDHLSL
        }

        Pass
        {
            Name "Outline"

            Cull Front
            HLSLPROGRAM
#pragma target 3.5
#pragma multi_compile_instancing
#pragma multi_compile _ STEREO_INSTANCING_ON
#pragma multi_compile _ MGFR_BUILD_STEREO_VARIANT
            #pragma vertex SChar_OutlineVert
            #pragma fragment SChar_OutlineFrag
            
            
            #pragma multi_compile_fwdbase

            #include "ZmdBuiltInCompat.cginc"

            #include "ZmdCharUtils.cginc"
            ENDHLSL
        }


        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            HLSLPROGRAM
#pragma target 3.5
#pragma multi_compile_instancing
#pragma multi_compile _ STEREO_INSTANCING_ON
#pragma multi_compile _ MGFR_BUILD_STEREO_VARIANT
            #pragma multi_compile_shadowcaster
            #pragma vertex SChar_ShadowVert
            #pragma fragment SChar_ShadowFrag

            #include "ZmdBuiltInCompat.cginc"
            #include "ZmdBuiltInCompat.cginc"

            #include "ZmdCharUtils.cginc"

            ENDHLSL
        }
    }
}
