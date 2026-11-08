Shader "Hidden/PostProcessing/DepthOffsetRim_PP"
{
    Properties
    {
        _MainTex ("Texture", 2D) = "white" {}
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline" = "UniversalPipeline" }
        LOD 100
        ZTest Always ZWrite Off Cull Off
        Blend One One

        Pass
        {
            Name "DepthOffsetRim"

            HLSLPROGRAM
            #pragma vertex FullscreenVert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            struct Attributes
            {
                uint vertexID : SV_VertexID;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
            };

            Varyings FullscreenVert(Attributes input)
            {
                Varyings output;
                output.positionCS = GetFullScreenTriangleVertexPosition(input.vertexID);
                output.uv = GetFullScreenTriangleTexCoord(input.vertexID);
                return output;
            }

            TEXTURE2D(_CharacterMaskTexture);
            SAMPLER(sampler_CharacterMaskTexture);

            float _OffsetMul;
            float _Threshold;
            float _Smooth;
            float4 _RimLightColor;
            float _RimIntensity;

            half4 frag(Varyings input) : SV_Target
            {
                float2 uv = input.uv;
                
                half charMask = SAMPLE_TEXTURE2D(_CharacterMaskTexture, sampler_CharacterMaskTexture, uv).r;
                if (charMask < 0.5) return half4(0, 0, 0, 0);

                float rawDepth = SampleSceneDepth(uv);
                
                #if UNITY_REVERSED_Z
                if (rawDepth <= 0.00001) return half4(0, 0, 0, 0);
                #else
                if (rawDepth >= 0.99999) return half4(0, 0, 0, 0);
                #endif
                
                float aspect = _ScreenParams.x / _ScreenParams.y;
                float2 offsetX = float2(_OffsetMul / aspect, 0);
                float2 offsetY = float2(0, _OffsetMul);
                
                float depthL = LinearEyeDepth(SampleSceneDepth(uv - offsetX), _ZBufferParams);
                float depthR = LinearEyeDepth(SampleSceneDepth(uv + offsetX), _ZBufferParams);
                float depthU = LinearEyeDepth(SampleSceneDepth(uv + offsetY), _ZBufferParams);
                float depthD = LinearEyeDepth(SampleSceneDepth(uv - offsetY), _ZBufferParams);
                
                float centerDepth = LinearEyeDepth(rawDepth, _ZBufferParams);
                
                float maxDiff = max(max(depthL - centerDepth, depthR - centerDepth), 
                                    max(depthU - centerDepth, depthD - centerDepth));
                
                float DOR_mask = smoothstep(_Threshold - _Smooth, _Threshold + _Smooth, maxDiff);
                
                half3 final_rim = DOR_mask * _RimLightColor.rgb * _RimIntensity;

                return half4(final_rim, 0.0);
            }
            ENDHLSL
        }
    }
}