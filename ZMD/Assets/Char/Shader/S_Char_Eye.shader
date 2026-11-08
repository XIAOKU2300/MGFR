Shader "ZMD/S_Char_Eye"
{
    Properties
    {
        [Header(Mode)]
        [Toggle(_USE_EYEBROW_MODE)] _UseEyebrowMode ("Use Eyebrow Mode", Float) = 0
        
        [Header(Map)]
        _BaseMap ("BaseColor", 2D) = "white" {}
        [Header(Iris Settings (Hidden in Eyebrow Mode))]
        _MatCapMap1 ("MatCap 1", 2D) = "black" {}
        _Mask ("Mask", 2D) = "white" {}
        _HighLightColor ("HighLight Color", Color) = (0, 0, 0, 1)
        _MatCapIntensity1 ("MatCap 1 Intensity", Range(0, 2)) = 1
        _MatCapIntensity2 ("MatCap 2 Intensity", Range(0, 10)) = 1
        _SphereMaskRange ("SphereMask Range", float) = 1
        _Parallax ("Parallax", float) = 0
        
        [Header(Shared Settings)]
        [Space(10)]
        [Header(Offset)]
        _Offset ("Offset", range(0, 0.1)) = 0
        
        [Header(Hair Occlusion)]
        _HairDepthFade ("Hair Depth Fade", Range(0, 1)) = 0.5
        _HairOcclusionColor ("Hair Occlusion Color", Color) = (0, 0, 0, 1)
        _HairOcclusionAlpha ("Hair Occlusion Alpha", Range(0, 1)) = 0.5
        
        [Header(Side Fade for Occluded Parts)]
        _SideFadeStart ("Side Fade Start (Angle Cosine)", Range(0, 1)) = 0.1
        _SideFadeEnd ("Side Fade End (Angle Cosine)", Range(0, 1)) = -0.1
        
        [HideInInspector] _StencilEyebrowRef ("Stencil Eyebrow Ref (Bitmask)", Float) = 128
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "Queue"="Transparent+1" "RenderPipeline"="UniversalPipeline" }
        LOD 100

        Pass
        {
            Stencil
            {
                Ref [_StencilEyebrowRef]
                ReadMask [_StencilEyebrowRef]
                WriteMask [_StencilEyebrowRef]
                Comp NotEqual
                Pass Replace
            }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            ZTest Always
            
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma shader_feature_local _USE_EYEBROW_MODE

            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/GlobalSamplers.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
                float3 normalOS : NORMAL;
                float4 tangentOS : TANGENT;
            };

            struct Varyings
            {
                float2 uv : TEXCOORD0;
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD1;
                float3 tangentWS : TEXCOORD2;
                float3 bitangentWS : TEXCOORD3;
                float3 positionWS : TEXCOORD4;
                float3 normalVS : TEXCOORD5;
                float4 screenPos : TEXCOORD6;
                float3 viewDirWS_Vert : TEXCOORD7;
            };

            TEXTURE2D(_BaseMap);
            SAMPLER(sampler_BaseMap);
            TEXTURE2D(_MatCapMap1);
            SAMPLER(sampler_MatCapMap1);
            TEXTURE2D(_Mask);
            SAMPLER(sampler_Mask);
            TEXTURE2D_X(_PerObjectTransparentDepthTexture);

            // 全局头部方向变量 (由 FaceDirection 脚本设置)
            float4 _HeadForward;

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseMap_ST;
                half4 _MatCapMap1_ST;
                half4 _Mask_ST;
                half _MatCapIntensity1;
                half _MatCapIntensity2;
                half3 _HighLightColor;
                half _SphereMaskRange;
                half _Parallax;
                float _Offset;
                float4 _HairOcclusionColor;
                float _HairDepthFade;
                float _HairOcclusionAlpha;
                float _SideFadeStart;
                float _SideFadeEnd;
            CBUFFER_END

            Varyings vert(Attributes i)
            {
                Varyings o;
                //摄像机偏移
                float3 positionWS = TransformObjectToWorld(i.positionOS.xyz);
                float3 offsetDir = normalize(_WorldSpaceCameraPos - positionWS);
                float3 offsetPositionWS = positionWS + offsetDir * _Offset;
                float3 offsetPositionOS = TransformWorldToObject(offsetPositionWS);

                o.positionCS = TransformObjectToHClip(offsetPositionOS);
                o.positionWS = TransformObjectToWorld(offsetPositionOS);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.tangentWS = TransformObjectToWorldDir(i.tangentOS.xyz);
                o.bitangentWS = cross(o.normalWS, o.tangentWS) * i.tangentOS.w;
                o.normalVS = mul((float3x3)GetWorldToViewMatrix(), o.normalWS);
                o.uv = TRANSFORM_TEX(i.uv, _BaseMap);
                o.screenPos = ComputeScreenPos(o.positionCS);
                o.viewDirWS_Vert = _WorldSpaceCameraPos - offsetPositionWS;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                half3 normalWS = normalize(i.normalWS);
                half3 viewDirWS = normalize(GetWorldSpaceViewDir(i.positionWS));
                
                #ifdef _USE_EYEBROW_MODE
                    half4 color = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv);
                    clip(color.a - 0.001h);

                    Light mainLight = GetMainLight();
                    half NdotL = saturate(dot(normalWS, mainLight.direction) + 0.5);
                    half3 diffuseLight = mainLight.color * NdotL;
                    half3 ambientLight = SampleSH(normalWS);
                    half3 final_col = color.rgb * max(diffuseLight, ambientLight);
                    
                    half baseAlpha = color.a;
                #else
                    half3 tangentWS = normalize(i.tangentWS);
                    half3 bitangentWS = normalize(i.bitangentWS);
                    
                    //视差
                    half2 uvMask = abs(i.uv - half2(0.5, 0.5)) * _SphereMaskRange;
                    half dist = length(uvMask);
                    half sphereMask = saturate(1.0 - dist * dist);

                    half3x3 TBN = half3x3(tangentWS, bitangentWS, normalWS);
                    float3 tanViewdir = normalize(mul(TBN, viewDirWS));
                    float2 para_offset = (tanViewdir.xy / (tanViewdir.z + 0.42f)) * _Parallax * sphereMask;
                    
                    //MatCap (基于UV构建伪球体法线)
                    half2 centeredUV = (i.uv - 0.5) * 2.0;
                    half sphereZ = sqrt(max(0.0, 1.0 - dot(centeredUV, centeredUV)));
                    half3 fakeNormalTS = normalize(half3(centeredUV.x, centeredUV.y, sphereZ));
                    half3 fakeNormalWS = normalize(mul(fakeNormalTS, TBN));
                    half3 fakeNormalVS = normalize(mul((float3x3)GetWorldToViewMatrix(), fakeNormalWS));
                    
                    half2 matcapUV1 = (fakeNormalVS.xy * 0.5 + 0.5) * _MatCapMap1_ST.xy + _MatCapMap1_ST.zw;
                    half3 matcapColor1 = SAMPLE_TEXTURE2D(_MatCapMap1, sampler_MatCapMap1, matcapUV1).rgb * _MatCapIntensity1;
                    half mask = SAMPLE_TEXTURE2D(_Mask, sampler_Mask, i.uv * _Mask_ST.xy + _Mask_ST.zw).r * _MatCapIntensity2;
                    half3 matcapColor = matcapColor1 + mask * _HighLightColor;

                    half3 BaseMap = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv + para_offset).rgb;
                    half3 final_col = BaseMap + matcapColor;
                    
                    half baseAlpha = 1.0h;
                #endif

                float2 screenUV = i.screenPos.xy / i.screenPos.w;
                float rawSceneDepth = SampleSceneDepth(screenUV);
                float sceneLinearDepth = LinearEyeDepth(rawSceneDepth, _ZBufferParams);
                float currentLinearDepth = i.screenPos.w;
                clip(sceneLinearDepth - currentLinearDepth);

                // 采样头发的深度图
                float2 hairUV = UnityStereoTransformScreenSpaceTex(screenUV);
                float rawHairDepth = SAMPLE_TEXTURE2D_X(_PerObjectTransparentDepthTexture, sampler_PointClamp, hairUV).r;
                float hairLinearDepth = LinearEyeDepth(rawHairDepth, _ZBufferParams);
                
                // 计算深度差
                float hairDepthDelta = currentLinearDepth - hairLinearDepth;

                half hairOcclusion = (half)smoothstep(0.0, max(_HairDepthFade, 0.0001), hairDepthDelta);
                final_col *= lerp(half3(1.0, 1.0, 1.0), _HairOcclusionColor.rgb, hairOcclusion * _HairOcclusionColor.a);
                
                // 仅对被头发遮挡的部分计算侧面视角渐隐
                half3 headForwardWS = normalize(_HeadForward.xyz);
                half3 vertViewDirWS = normalize(i.viewDirWS_Vert);
                half FdotV = dot(headForwardWS, vertViewDirWS);
                
                half sideFade = smoothstep(_SideFadeEnd, max(_SideFadeStart, _SideFadeEnd + 0.0001), FdotV);
                
                half occludedAlpha = _HairOcclusionAlpha * sideFade;
                half targetAlpha = lerp(1.0h, occludedAlpha, hairOcclusion);
                
                half finalAlpha = baseAlpha * targetAlpha;

                return half4(final_col, finalAlpha);
            }
            ENDHLSL
        }
    }
}
