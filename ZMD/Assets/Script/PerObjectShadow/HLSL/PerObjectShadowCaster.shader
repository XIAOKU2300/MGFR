Shader "Hidden/PerObjectShadowCaster"
{
    // 该 Shader 包含三个核心部分：
    // 1. ShadowCaster Pass: 用于将物体渲染到 ShadowMap Atlas 中
    // 2. Volume_Env Pass: 环境阴影体积投影
    // 3. Volume_Self Pass: 角色自阴影体积投影（带 Stencil 过滤）
    Properties
    {
        _StencilRef("Stencil Ref", Float) = 1
    }

    SubShader
    {
        Tags 
        { 
            "RenderType" = "Opaque" 
            "RenderPipeline" = "UniversalPipeline" 
        }
        
        // ==================== Pass 1: ShadowCaster (生成阴影图) ====================
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
            };

            float3 _LightDirection;
            float4 _ShadowBias; // x: depthBias, y: normalBias

            // 简易阴影偏移计算
            float3 ApplyShadowBiasSimple(float3 positionWS, float3 normalWS, float3 lightDirectionWS)
            {
                positionWS = positionWS + lightDirectionWS * _ShadowBias.x;
                positionWS = positionWS + normalWS * _ShadowBias.y;
                return positionWS;
            }

            Varyings Vert(Attributes input)
            {
                Varyings output;
                float3 positionWS = TransformObjectToWorld(input.positionOS.xyz);
                float3 normalWS = TransformObjectToWorldNormal(input.normalOS);
                positionWS = ApplyShadowBiasSimple(positionWS, normalWS, _LightDirection);
                output.positionCS = TransformWorldToHClip(positionWS);
                return output;
            }

            half4 Frag(Varyings input) : SV_Target
            {
                return 0;
            }
            ENDHLSL
        }

        // ==================== Pass 2: PerObjectShadowVolume_Env (环境投影) ====================
        Pass
        {
            Name "PerObjectShadowVolume_Env"
            
            ZTest Greater // 配合 Cull Front 实现体积内部渲染
            ZWrite Off
            Cull Front

            Blend One One
            BlendOp Min // 取阴影最深处

            Stencil
            {
                Ref 0
                Comp Equal
                Pass Keep
            }

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex VolumeVert
            #pragma fragment VolumeFrag
            #pragma multi_compile _ _PCF_LOW _PCF_MEDIUM _PCF_HIGH

            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/GlobalSamplers.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            TEXTURE2D_SHADOW(_PerObjectShadowmapTexture);
            SamplerComparisonState sampler_LinearClampCompare;

            float4x4 _VolumeWorldToShadow;  // 世界到阴影投影空间
            float4x4 _VolumeWorldToShadowClip;  // 世界到阴影裁剪空间（用于裁剪）
            float4 _VolumeUvScaleOffset;    // Atlas Tile 偏移
            float4 _PerObjectShadowParams;  // x:强度, y:Ramp强度, z:软阴影开关
            float4 _PerObjectShadowAtlasSize;

            #include "PerObjectShadowVolumeInclude.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "PerObjectShadowVolume_EnvAll"

            ZTest Greater
            ZWrite Off
            Cull Front

            Blend One One
            BlendOp Min

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex VolumeVert
            #pragma fragment VolumeFrag
            #pragma multi_compile _ _PCF_LOW _PCF_MEDIUM _PCF_HIGH

            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/GlobalSamplers.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            TEXTURE2D_SHADOW(_PerObjectShadowmapTexture);
            SamplerComparisonState sampler_LinearClampCompare;

            float4x4 _VolumeWorldToShadow;
            float4x4 _VolumeWorldToShadowClip;
            float4 _VolumeUvScaleOffset;
            float4 _PerObjectShadowParams;
            float4 _PerObjectShadowAtlasSize;

            #include "PerObjectShadowVolumeInclude.hlsl"
            ENDHLSL
        }

        // ==================== Pass 3: PerObjectShadowVolume_Self (自阴影投影) ====================
        Pass
        {
            Name "PerObjectShadowVolume_Self"
            
            ZTest Greater
            ZWrite Off
            Cull Front

            Blend One One
            BlendOp Min

            Stencil
            {
                Ref [_StencilRef]
                Comp Equal
                Pass Keep
            }

            HLSLPROGRAM
            #pragma target 3.0
            #pragma vertex VolumeVert
            #pragma fragment VolumeFrag
            #pragma multi_compile _ _PCF_LOW _PCF_MEDIUM _PCF_HIGH

            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/GlobalSamplers.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            TEXTURE2D_SHADOW(_PerObjectShadowmapTexture);
            SamplerComparisonState sampler_LinearClampCompare;

            float4x4 _VolumeWorldToShadow;
            float4x4 _VolumeWorldToShadowClip;
            float4 _VolumeUvScaleOffset;
            float4 _PerObjectShadowParams;
            float4 _PerObjectShadowAtlasSize;

            #include "PerObjectShadowVolumeInclude.hlsl"
            ENDHLSL
        }
    }
}
