Shader "Custom/RainDropsWithReflection"
{
    Properties
    {
        [Header(Global Rain Controls)]
        [Toggle(_ENABLE_RAIN_DROPS)] _Enable_RainDrops("Enable Rain Drops", Float) = 1.0
        [Toggle(_ENABLE_RAIN_DRIPS)] _Enable_RainDrips("Enable Rain Drips", Float) = 1.0
        _Rain_Smoothness("Rain Smoothness", Range(0, 1)) = 0.9
        _Rain_EnvSmoothness("Rain Env Smoothness", Range(0, 1)) = 0.9

        //===== Rain Drops Settings =====
        [Header(Rain Drops)]
        [NoScaleOffset]_RainDrop_Tex("Texture (RG:Norm, B:Phase, A:Mask)", 2D) = "black" {}
        _RainDrop_Tiling("Tiling", Range(0.01, 10)) = 1.0
        _RainDrop_Intensity("Intensity", Range(0, 1)) = 1.0
        _RainDrop_Density("Density", Range(0, 1)) = 0.5
        _RainDrop_Speed("Speed", Range(0, 2)) = 0.5
        _RainDrop_NormalYOffset("Normal Y Offset", Range(-1, 1)) = 0.0
        _RainDrop_EdgeSmoothness("Edge Smoothness", Range(0.1, 20)) = 5.0

        //===== Rain Drips Settings =====
        [Header(Rain Drips)]
        [NoScaleOffset]_RainDrip_Tex("Texture (RG:Norm, B:Mask, A:Offset)", 2D) = "black" {}
        [NoScaleOffset]_RainDrip_MaskTex("Mask Texture (R:Mask)", 2D) = "white" {}
        _RainDrip_Tiling("Tiling", Range(0.01, 10)) = 1.0
        _RainDrip_Intensity("Intensity", Range(0, 1)) = 1.0
        _RainDrip_Speed("Speed", Range(0, 20)) = 1.0
        _RainDrip_NormalYOffset("Normal Y Offset", Range(-1, 1)) = 0.0
        _RainDrip_EdgeSmoothness("Edge Smoothness", Range(0.1, 20)) = 5.0
        _RainDrip_TriplanarSharpness("Triplanar Sharpness", Range(1, 64)) = 4.0

        //===== General & Reflection Settings =====
        [Header(Base)]
        _BaseMap("Base Texture", 2D) = "white" {}
        _BaseColor("Base Color", Color) = (1,1,1,1)
        _Metallic("Metallic", Range(0, 1)) = 0.0
        _Smoothness("Smoothness", Range(0, 1)) = 0.5
        
        [Header(Environment Reflection)]
        _EnvSmoothness("Env Smoothness", Range(0, 1)) = 0.5
        _EnvSpecularColor("Env Specular Color", Color) = (1,1,1,1)
        _EnvSpecularIntensity("Env Specular Intensity", Range(0, 5)) = 1.0
        
        [Header(Direct Specular)]
        _SpecularColor("Specular Color", Color) = (1,1,1,1)
        _SpecularIntensity("Specular Intensity", Range(0, 5)) = 1.0
        _SpecShininese("Spec Shininess", Range(1, 128)) = 10.0
    }

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        LOD 100

        Pass
        {
            Name "ForwardLit"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma shader_feature _ENABLE_RAIN_DROPS
            #pragma shader_feature _ENABLE_RAIN_DRIPS
            
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            //===== Textures & Samplers =====
            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            TEXTURE2D(_RainDrop_Tex); SAMPLER(sampler_RainDrop_Tex);
            TEXTURE2D(_RainDrip_Tex); SAMPLER(sampler_RainDrip_Tex);
            TEXTURE2D(_RainDrip_MaskTex); SAMPLER(sampler_RainDrip_MaskTex);

            CBUFFER_START(UnityPerMaterial)
                // Global Rain Controls
                float _Rain_Smoothness;
                float _Rain_EnvSmoothness;

                // Rain Drop Core
                float _RainDrop_Tiling;
                float _RainDrop_Intensity;
                float _RainDrop_Density;
                float _RainDrop_Speed;
                float _RainDrop_NormalYOffset;
                float _RainDrop_EdgeSmoothness;
                
                // Rain Drip Core
                float _RainDrip_Tiling;
                float _RainDrip_Intensity;
                float _RainDrip_Speed;
                float _RainDrip_NormalYOffset;
                float _RainDrip_EdgeSmoothness;
                float _RainDrip_TriplanarSharpness;
                
                // General & Reflection
                float4 _BaseMap_ST;
                float4 _BaseColor;
                float _Metallic;
                float _Smoothness;
                float _EnvSmoothness;
                float4 _EnvSpecularColor;
                float _EnvSpecularIntensity;

                float4 _SpecularColor;
                float _SpecularIntensity;
                float _SpecShininese;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 normalWS : TEXCOORD3;
                float3 tangentWS : TEXCOORD4;
                float3 bitangentWS : TEXCOORD5;
                float3 positionWS : TEXCOORD6;
            };

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs vertexInput = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = vertexInput.positionCS;
                output.positionWS = vertexInput.positionWS;
                output.uv = TRANSFORM_TEX(input.uv, _BaseMap);

                VertexNormalInputs normalInput = GetVertexNormalInputs(input.normalOS, input.tangentOS);
                output.normalWS = normalInput.normalWS;
                output.tangentWS = normalInput.tangentWS;
                output.bitangentWS = normalInput.bitangentWS;

                return output;
            }

            half4 SampleTriplanar(Texture2D tex, SamplerState samp, float3 posWS, float3 normalWS, float tiling, float sharpness)
            {
                // 计算三面混合权重
                float3 blendWeights = pow(abs(normalWS), sharpness);
                blendWeights = blendWeights / (blendWeights.x + blendWeights.y + blendWeights.z);

                // 计算三个平面的 UV
                float2 uvX = posWS.zy * tiling;
                float2 uvY = posWS.xz * tiling;
                float2 uvZ = posWS.xy * tiling;

                // 分别采样三个平面
                half4 colX = tex.Sample(samp, uvX);
                half4 colY = tex.Sample(samp, uvY);
                half4 colZ = tex.Sample(samp, uvZ);

                // 混合结果
                return colX * blendWeights.x + colY * blendWeights.y + colZ * blendWeights.z;
            }
            
            half4 frag(Varyings input) : SV_Target
            {
                float3 normalWS = normalize(input.normalWS);
                float3 rainNormalTS = float3(0, 0, 1);
                float dropMask = 0;
                float staticDropMask = 0;
                float dripMask = 0;
                float staticDripMask = 0;

                #ifdef _ENABLE_RAIN_DROPS
                //=========================================================
                // 1. Rain Drops Core Logic
                //=========================================================
                float2 rainUV = input.positionWS.xz * _RainDrop_Tiling;
                half4 rainSample = SAMPLE_TEXTURE2D(_RainDrop_Tex, sampler_RainDrop_Tex, rainUV);
                
                // 世界法线 Y 遮罩
                half normalYMask = saturate(saturate(normalWS.y + _RainDrop_NormalYOffset) * _RainDrop_EdgeSmoothness);

                // 动画与强度掩码
                float timeDrops = _Time.y * _RainDrop_Speed;
                float dropAnim = frac(rainSample.b - timeDrops);
                float densityMask = step(1.0 - _RainDrop_Density, rainSample.b);
                float dropMaskRaw = rainSample.a * 2.0 - 1.0;
                
                // 动态掩码 (带时间)
                dropMask = (saturate(dropMaskRaw) * dropAnim + saturate(-dropMaskRaw)) * _RainDrop_Intensity * normalYMask * densityMask;
                // 静态掩码 (不带时间)
                staticDropMask = (saturate(dropMaskRaw) + saturate(-dropMaskRaw)) * _RainDrop_Intensity * normalYMask * densityMask;
                
                // 法线解包 (取反 XY 以使其凸出)
                rainNormalTS.xy = (rainSample.rg * 2.0 - 1.0) * dropMask * -1.0;
                rainNormalTS.z = sqrt(saturate(1.0 - dot(rainNormalTS.xy, rainNormalTS.xy)));
                #endif

                #ifdef _ENABLE_RAIN_DRIPS
                //=========================================================
                // 1.5 Rain Drips Core Logic
                //=========================================================
                // 1. 使用三面投射采样流雨基础数据
                half4 dripSample = SampleTriplanar(_RainDrip_Tex, sampler_RainDrip_Tex, input.positionWS, input.normalWS, _RainDrip_Tiling, _RainDrip_TriplanarSharpness);
                
                // 2. 侧面投影与遮罩滚动 (Time与Offset相加，实现顺滑滚动)
                float timeOffset = dripSample.a;
                float2 dripMaskUV = input.positionWS.yx + (_Time.y * _RainDrip_Speed + timeOffset).xx;
                float2 staticDripMaskUV = input.positionWS.yx + timeOffset.xx; // 不带时间的 UV
                
                half dripMaskSample = SAMPLE_TEXTURE2D(_RainDrip_MaskTex, sampler_RainDrip_MaskTex, dripMaskUV).r;
                half staticDripMaskSample = SAMPLE_TEXTURE2D(_RainDrip_MaskTex, sampler_RainDrip_MaskTex, staticDripMaskUV).r;
                
                // 侧面遮罩：仅在垂直面上显示流雨
                half dripSideMask = saturate(saturate(1.0 - abs(normalWS.y) - _RainDrip_NormalYOffset) * _RainDrip_EdgeSmoothness);
                
                // 动态掩码 (带时间)
                dripMask = dripSample.b * dripMaskSample * _RainDrip_Intensity * dripSideMask;
                // 静态掩码 (不带时间)
                staticDripMask = dripSample.b * _RainDrip_Intensity * dripSideMask;
                
                float3 dripNormalTS;
                dripNormalTS.xy = (dripSample.rg * 2.0 - 1.0) * dripMask * -1.0;
                dripNormalTS.z = sqrt(saturate(1.0 - dot(dripNormalTS.xy, dripNormalTS.xy)));

                //=========================================================
                // 1.8 Blend Rain Drops & Drips
                //=========================================================
                // 使用 RNM 算法混合雨滴与流雨的切线空间法线
                float3 n1 = rainNormalTS + float3(0, 0, 1);
                float3 n2 = dripNormalTS * float3(-1, -1, 1);
                rainNormalTS = n1 * dot(n1, n2) / n1.z - n2;
                #endif
                
                // 混合雨水掩码
                float finalRainMask = saturate(dropMask + dripMask);
                float staticRainMask = saturate(staticDropMask + staticDripMask); // 混合后的静态掩码
                finalRainMask = max(finalRainMask, staticRainMask * 0.5);

                // 转换到世界空间
                float3x3 TBN = float3x3(input.tangentWS, input.bitangentWS, normalWS);
                float3 combinedNormalWS = normalize(mul(rainNormalTS, TBN));


                //=========================================================
                // 2. General Shading & Reflection Utils
                //=========================================================
                // 基础贴图
                half4 baseColor = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;

                // 获取主光源
                Light mainLight = GetMainLight();
                float3 viewDirWS = normalize(GetCameraPositionWS() - input.positionWS);
                half3 lightDir = mainLight.direction;

                // 1. 直接光漫反射 (Half Lambert)
                half halfLambert = dot(combinedNormalWS, lightDir) * 0.5 + 0.5;
                half3 diffColor = baseColor.rgb * (1.0 - _Metallic);
                half3 finalDiff = diffColor * halfLambert * mainLight.color;

                // 2. 直接光高光 (参考 S_Char_Cloth)
                half finalSmoothness = lerp(_Smoothness, _Rain_Smoothness, finalRainMask);
                half3 halfDir = normalize(viewDirWS + lightDir);
                half NdotH = max(0, dot(combinedNormalWS, halfDir));
                half VdotH = max(0, dot(viewDirWS, halfDir));
                
                half shininess = lerp(1.0, _SpecShininese, finalSmoothness); 
                half energyConservation = (shininess + 2.0) / (8.0 * 3.1415926); 
                
                // Fresnel 效应 (金属度影响 F0)
                half3 spec_color = lerp(half3(0.04, 0.04, 0.04), baseColor.rgb, _Metallic);
                half3 fresnelTerm = spec_color + (1.0 - spec_color) * pow(1.0 - VdotH, 5.0);
                
                half spec_temp = pow(NdotH, shininess) * energyConservation;
                half3 final_spec = fresnelTerm * mainLight.color * _SpecularColor.rgb * _SpecularIntensity * spec_temp * halfLambert;

                // 3. 间接光漫反射 (SH)
                half3 ambient = SampleSH(combinedNormalWS);
                half3 final_env_diff = ambient * diffColor;

                // 4. 环境反射 (间接高光)
                half3 reflectDir = reflect(-viewDirWS, combinedNormalWS);
                half NdotV = max(0, dot(combinedNormalWS, viewDirWS));
                
                half finalEnvSmoothness = lerp(_EnvSmoothness, _Rain_EnvSmoothness, finalRainMask);
                half envRoughness = 1.0 - finalEnvSmoothness;
                envRoughness = envRoughness * (1.7 - 0.7 * envRoughness);
                half3 envMap = GlossyEnvironmentReflection(reflectDir, input.positionWS, envRoughness, 1.0);
                
                half3 envFresnel = spec_color + (max(finalSmoothness.xxx, spec_color) - spec_color) * pow(1.0 - NdotV, 5.0);
                half3 final_env_spec = envMap * envFresnel * _EnvSpecularColor.rgb * _EnvSpecularIntensity * halfLambert;
                
                // 最终颜色合成
                half3 finalColor = finalDiff + final_spec + final_env_diff + final_env_spec;

                return half4(finalColor, baseColor.a);
            }
            ENDHLSL
        }
    }
}
//v3uaf9pqem@usa.edu.pl NaILEn^!#@B2