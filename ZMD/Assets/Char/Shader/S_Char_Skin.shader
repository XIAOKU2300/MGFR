Shader "ZMD/S_Char_Skin"
{
    Properties
    {
        // =================================================================================
        [Header(Surface Maps)]
        _BaseColor ("Base Color", 2D) = "white" {}
        _NormalMap ("Normal Map", 2D) = "bump" {}
        _DiffuseRamp ("Diffuse Ramp (NPR)", 2D) = "white" {}

        // =================================================================================
        [Header(Surface Options)]
        _AlphaClip ("Alpha Clip Threshold", Range(0, 1)) = 0.5

        // =================================================================================
        [Header(Base Color)]
        _SecondColor ("Second Color", Color) = (1, 1, 1, 1)
        _DarkColor ("Dark Color", Color) = (0.5, 0.5, 0.5, 1)
        _RampStrength ("NPR Ramp Strength", Range(0, 1)) = 1.0
        _DarkIntensity ("Dark Area Intensity", Range(0, 5)) = 1.5
        _AO_Offset ("AO Offset", range(-1, 1)) = 0

        // =================================================================================
        [Header(Shadow)]
        _ShadowColor ("Shadow Color", Color) = (0.5, 0.5, 0.5, 1)
        _ShadowStrength ("Shadow Strength", Range(0, 1)) = 1.0

        // =================================================================================
        [Header(Fresnel)]
        _FresnelBias ("Fresnel Bias", Range(0, 1)) = 0
        _FresnelIntensity ("Fresnel Intensity", Range(0, 5)) = 1
        _FresnelPower ("Fresnel Power", Range(1, 10)) = 3

        // =================================================================================
        [Header(Specular)]
        _SpecularColor ("Specular Color", Color) = (1, 1, 1, 1)
        _SpecularIntensity ("Specular Intensity", Range(0, 5)) = 0.5
        _SpecShininese ("Specular Shininess", Range(2, 100)) = 32

        // =================================================================================
        [Header(Outline)]
        _OutLine ("Outline Width", range(0, 5)) = 1
        _OutLineColor ("Outline Color", Color) = (1, 1, 1, 1)
        [HideInInspector] _StencilRef("Stencil Ref", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        LOD 100

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            Stencil
            {
                Ref [_StencilRef]
                Comp Always
                Pass Replace
            }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma multi_compile _ _SHADOWS_SOFT

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
                float4 color : COLOR;
            };

            struct Varyings
            {
                float2 uv : TEXCOORD0;
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD1;
                float3 positionWS : TEXCOORD2;
                float4 shadowCoord : TEXCOORD3;
                float3 positionOS : TEXCOORD4;
                float4 positionNDC : TEXCOORD5;
                float3 positionVS : TEXCOORD6;
                float4 perObjectShadowCoord : TEXCOORD7;
                float3 tangentWS : TEXCOORD8;
                float3 bitangentWS : TEXCOORD9;
                float4 color : COLOR;
            };

            TEXTURE2D(_BaseColor);
            SAMPLER(sampler_BaseColor);
            TEXTURE2D(_NormalMap);
            SAMPLER(sampler_NormalMap);
            TEXTURE2D(_DiffuseRamp);
            SAMPLER(sampler_DiffuseRamp);

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor_ST;
                half _AlphaClip;
                half _RampStrength;
                half _DarkIntensity;
                half4 _SecondColor;
                half4 _DarkColor;
                half _AO_Offset;
                half4 _ShadowColor;
                half _ShadowStrength;
                half _FresnelBias;
                half _FresnelIntensity;
                half _FresnelPower;
                half4 _SpecularColor;
                half _SpecularIntensity;
                half _SpecShininese;
            CBUFFER_END

            #define S_CHAR_FORWARD_PASS
            #include "Packages/com.zmd.shaderlibrary/S_Char_Utils.hlsl"

            half4 TransformClipToViewPortPos(half4 positionCS)
            {
                half4 o = positionCS * 0.5f;
                o.xy = float2(o.x, o.y * _ProjectionParams.x) + o.w;
                o.zw = positionCS.zw;
                return o / o.w;
            }
            Varyings vert (Attributes v)
            {
                Varyings o;
                VertexPositionInputs vertexInput = GetVertexPositionInputs(v.positionOS.xyz);
                VertexNormalInputs normalInput = GetVertexNormalInputs(v.normalOS, v.tangentOS);

                o.positionCS = vertexInput.positionCS;
                o.positionWS = vertexInput.positionWS;
                o.positionNDC = vertexInput.positionNDC;
                o.positionVS = vertexInput.positionVS;

                o.normalWS = normalInput.normalWS;
                o.tangentWS = normalInput.tangentWS;
                o.bitangentWS = normalInput.bitangentWS;
                o.shadowCoord = GetShadowCoord(vertexInput);
                o.perObjectShadowCoord = ComputeScreenPos(vertexInput.positionCS);
                o.positionOS = v.positionOS.xyz;
                o.uv = TRANSFORM_TEX(v.uv, _BaseColor);
                o.color = v.color;
                return o;
            }

            half4 frag (Varyings i) : SV_Target
            {
                //输入
                half4 baseMap = SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, i.uv);
                half ao = saturate(baseMap.a + _AO_Offset);

                //法线与向量
                half3 normalTS = UnpackNormal(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, i.uv));
                normalTS = lerp(half3(0, 0, 1), normalTS, i.color.r);
                half3x3 TBN = half3x3(i.tangentWS, i.bitangentWS, i.normalWS);
                half3 normalWS = normalize(mul(normalTS, TBN));
                half3 viewDirWS = normalize(GetWorldSpaceViewDir(i.positionWS));
                Light mainLight = GetMainLight(i.shadowCoord);

                // 阴影
                
                half3 screenShadow = saturate(SamplePerObjectScreenSpaceShadowmap(i.perObjectShadowCoord));
                half finalShadowStrength = _Global_ShadowStrength * _ShadowStrength;
                half3 coloredShadow = lerp(_ShadowColor.rgb, half3(1.0, 1.0, 1.0), screenShadow.x);
                half3 perObjectShadow = lerp(half3(1.0, 1.0, 1.0), screenShadow, finalShadowStrength) * coloredShadow;
                half unityShadow = lerp(1.0, mainLight.shadowAttenuation, _Global_ShadowStrength);
                
                half3 shadowAtten = perObjectShadow;

                // 间接光漫反射
                half3 ambient = SampleSH(half3(0, 0, 0));
                half3 final_env = lerp(ambient * baseMap.rgb * _DarkColor.rgb, half3(0, 0, 0), shadowAtten.x);

                // 漫反射与 SSS 模拟
                half NdotL = dot(normalWS, mainLight.direction);
                half halfLambert = min(saturate((NdotL * 0.5 + 0.5) + 0.2), unityShadow);
                half3 ramp = SAMPLE_TEXTURE2D(_DiffuseRamp, sampler_DiffuseRamp, half2(halfLambert, 0.5)).rgb;
                
                half NdotV = 1 - max(0, dot(normalWS, viewDirWS));
                half fresnel = saturate(_FresnelBias + _FresnelIntensity * pow(NdotV, _FresnelPower));
                half3 second_col = _SecondColor * baseMap.rgb;
                half3 diffuse = lerp(baseMap.rgb, second_col, fresnel * i.color.r) * _DarkColor.rgb;
                
                half3 diffuseDark = diffuse * ambient * _DarkIntensity;
                half3 baseDiffuseLight = diffuse * halfLambert * mainLight.color;
                // Soft Light 公式: (1 - 2*b)*a^2 + 2*b*a
                half3 softLightRamp = BlendSoftLight(baseDiffuseLight, ramp);
                half3 diffuseLight = lerp(baseDiffuseLight, softLightRamp, _RampStrength);
                
                half3 final_diff = max(diffuseDark, diffuseLight) * ao * shadowAtten;

                // 高光计算 (Blinn-Phong)
                half3 halfDir = normalize(mainLight.direction + viewDirWS);
                half spec = pow(saturate(dot(normalWS, halfDir)), _SpecShininese);
                half3 final_spec = spec * _SpecularColor.rgb * _SpecularIntensity * screenShadow;

                // 调用全局封装的角色边缘光计算
                half3 inner_rim = 0;
                half3 final_rim = 0;
                CalculateAnimeRimLight(normalWS, viewDirWS, NdotL, screenShadow, baseMap.rgb, i.positionVS, i.positionNDC, i.positionOS, inner_rim, final_rim);

                // 最终颜色组合
                half3 finalColor = final_diff + final_spec + final_rim + inner_rim;

                return half4(finalColor, 1.0);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            HLSLPROGRAM
            #pragma vertex SChar_ShadowVert
            #pragma fragment SChar_ShadowFrag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.zmd.shaderlibrary/S_Char_Utils.hlsl"

            ENDHLSL
        }

        Pass
        {
            Name "Outline"

            Cull Front
            HLSLPROGRAM
            #pragma vertex SChar_OutlineVert
            #pragma fragment SChar_OutlineFrag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            #include "Packages/com.zmd.shaderlibrary/S_Char_Utils.hlsl"

            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }

            Stencil
            {
                Ref [_StencilRef]
                Comp Always
                Pass Replace
            }

            ZWrite On
            ZTest LEqual
            ColorMask R
            Cull Back

            HLSLPROGRAM
            #pragma target 2.0
            #pragma vertex DepthOnlyVertex
            #pragma fragment DepthOnlyFragment

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D(_BaseColor);
            SAMPLER(sampler_BaseColor);

            CBUFFER_START(UnityPerMaterial)
                float4 _BaseColor_ST;
                half _AlphaClip;
            CBUFFER_END

            struct DepthOnlyAttributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct DepthOnlyVaryings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            DepthOnlyVaryings DepthOnlyVertex(DepthOnlyAttributes input)
            {
                DepthOnlyVaryings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.uv = TRANSFORM_TEX(input.uv, _BaseColor);
                return output;
            }

            half DepthOnlyFragment(DepthOnlyVaryings input) : SV_TARGET
            {
                half alpha = SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, input.uv).a;
                clip(alpha - _AlphaClip);
                return input.positionCS.z;
            }
            ENDHLSL
        }

    }
}
