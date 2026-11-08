Shader "PerObjectShadow/ScreenSpaceShadowReceiver"
{
    Properties
    {
        _MaskMap("Mask Map", 2D) = "white" {}
        _Color1("Lerp Color 1", Color) = (1, 1, 1, 1)
        _Color2("Lerp Color 2", Color) = (0, 0, 0, 1)
        [HideInInspector] _StencilRef("Stencil Ref", Float) = 0
    }
    SubShader
    {
        Tags
        {
            "RenderType" = "Opaque"
            "RenderPipeline" = "UniversalPipeline"
            "UniversalMaterialType" = "Unlit"
            "Queue" = "Geometry"
        }

        Pass
        {
            Name "UniversalForward"
            Tags { "LightMode" = "UniversalForward" }

            Stencil
            {
                Ref 0
                Comp Equal
                Pass Replace
            }

            ZWrite On
            ZTest LEqual
            Cull Back

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #pragma multi_compile_fragment _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fog
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION

            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/GlobalSamplers.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Input.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/ShaderVariablesFunctions.hlsl"


            #define S_CHAR_FORWARD_PASS
            #include "Packages/com.zmd.shaderlibrary/S_Char_Utils.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _Color1;
                float4 _Color2;
                float4 _MaskMap_ST;
            CBUFFER_END

            TEXTURE2D(_MaskMap);
            SAMPLER(sampler_MaskMap);

            // ================== 环境阴影强度 ==================
            float _Global_EnvShadowStrength;

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD0;
                float2 uv : TEXCOORD1;
                float4 shadowCoord : TEXCOORD2;
                float3 positionWS : TEXCOORD3;
                float fogCoord : TEXCOORD4;
            };

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs posInput = GetVertexPositionInputs(input.positionOS.xyz);
                output.positionCS = posInput.positionCS;
                output.normalWS = TransformObjectToWorldNormal(input.normalOS);
                output.uv = TRANSFORM_TEX(input.uv, _MaskMap);
                output.shadowCoord = ComputeScreenPos(posInput.positionCS);
                output.positionWS = posInput.positionWS;
                output.fogCoord = ComputeFogFactor(posInput.positionCS.z);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                float3 normalWS = SafeNormalize(input.normalWS);

                float4 mainShadowCoord = TransformWorldToShadowCoord(input.positionWS);
                Light mainLight = GetMainLight(mainShadowCoord);

                float ndotl = saturate(dot(normalWS, mainLight.direction));

                // 阴影
                half unityShadow = lerp(half3(1.0, 1.0, 1.0), mainLight.shadowAttenuation, _Global_EnvShadowStrength);
                
                half3 screenShadow = saturate(SamplePerObjectScreenSpaceShadowmap(input.shadowCoord));
                screenShadow = lerp(half3(1.0, 1.0, 1.0), screenShadow, _Global_EnvShadowStrength);
                
                half3 shadowAtten = min(screenShadow, unityShadow.xxx);

                // 获取SSAO
                float2 normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(input.positionCS);
                AmbientOcclusionFactor aoFactor = GetScreenSpaceAmbientOcclusion(normalizedScreenSpaceUV);
                shadowAtten *= aoFactor.directAmbientOcclusion;

                half mask = SAMPLE_TEXTURE2D(_MaskMap, sampler_MaskMap, input.uv).r;
                half4 lerpedColor = lerp(_Color1, _Color2, mask);
                
                half3 lit = lerpedColor.rgb * (ndotl * shadowAtten) * mainLight.color;
                lit = MixFog(lit, input.fogCoord);
                
                return half4(lit, lerpedColor.a);
            }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }

            Stencil
            {
                Ref 0
                Comp Equal
                Pass Replace
            }

            ZWrite On
            ColorMask R
            Cull Back

            HLSLPROGRAM
            #pragma target 2.0
            #pragma vertex DepthOnlyVertex
            #pragma fragment DepthOnlyFragment

            #pragma multi_compile_instancing

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct DepthOnlyAttributes
            {
                float4 positionOS : POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct DepthOnlyVaryings
            {
                float4 positionCS : SV_POSITION;
                UNITY_VERTEX_INPUT_INSTANCE_ID
                UNITY_VERTEX_OUTPUT_STEREO
            };

            DepthOnlyVaryings DepthOnlyVertex(DepthOnlyAttributes input)
            {
                DepthOnlyVaryings output = (DepthOnlyVaryings)0;
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_TRANSFER_INSTANCE_ID(input, output);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(output);

                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                return output;
            }

            half DepthOnlyFragment(DepthOnlyVaryings input) : SV_TARGET
            {
                UNITY_SETUP_INSTANCE_ID(input);
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(input);
                return input.positionCS.z;
            }
            ENDHLSL
        }
    }
}
