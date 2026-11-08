Shader "ZMD/S_Char_Shadow"
{
    Properties
    {
        _TransparentColor ("Transparent Color", Color) = (1, 1, 1, 1)
        _DepthClip ("DepthClip", float) = 0.5
        
        [Header(Eye Shadow Mode)]
        [Toggle(_USE_EYE_SHADOW)] _UseEyeShadow ("Use Eye Shadow Mode", Float) = 0
        _ShadowMask ("ShadowMask (Eye Mode)", 2D) = "white" {}
        _EyeShadowOffset ("EyeShadow Offset", float) = 0.1
    }
    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent-1" }
        LOD 100

        Pass
        {
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma shader_feature_local _USE_EYE_SHADOW

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float4 screenUV : TEXCOORD0;
                float2 uv : TEXCOORD1;
            };

            TEXTURE2D(_ShadowMask);
            SAMPLER(sampler_ShadowMask);

            CBUFFER_START(UnityPerMaterial)
                float4 _TransparentColor;
                float _DepthClip;
                half4 _ShadowMask_ST;
                half _EyeShadowOffset;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                
                #ifdef _USE_EYE_SHADOW
                    float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                    float3 offsetDir = normalize(_WorldSpaceCameraPos - positionWS);
                    float3 offsetPositionWS = positionWS + offsetDir * _EyeShadowOffset;
                    float3 offsetPositionOS = TransformWorldToObject(offsetPositionWS);
                    output.positionCS = TransformObjectToHClip(offsetPositionOS);
                    output.uv = TRANSFORM_TEX(input.uv, _ShadowMask);
                #else
                    output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                #endif
                
                output.screenUV = ComputeScreenPos(output.positionCS);
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                #ifdef _USE_EYE_SHADOW
                    half shadowMask = SAMPLE_TEXTURE2D(_ShadowMask, sampler_ShadowMask, input.uv).r;
                    shadowMask = saturate(shadowMask * _TransparentColor.a);
                    return half4(_TransparentColor.rgb, shadowMask);
                #else
                    float2 grabUV = input.screenUV.xy / input.screenUV.w;
                    
                    //深度剔除
                    float rawDepth = SampleSceneDepth(grabUV);
                    float eyeDepth = LinearEyeDepth(rawDepth, _ZBufferParams);

                    float4 ScreenPosNorm = float4(GetNormalizedScreenSpaceUV(input.positionCS), input.positionCS.zw);
                    float4 ClipPos = ComputeClipSpacePosition(ScreenPosNorm.xy, input.positionCS.z) * input.positionCS.w;
                    float4 ScreenPos = ComputeScreenPos(ClipPos);
                    float alpha = (step((eyeDepth - ScreenPos.w) , _DepthClip)) * _TransparentColor.a;
                    clip(alpha - 0.001);
                    
                    return half4(_TransparentColor.rgb, alpha);
                #endif
            }
            ENDHLSL
        }
    }
}
