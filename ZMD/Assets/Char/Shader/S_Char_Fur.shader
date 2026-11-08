Shader "ZMD/Fur_RendererFeature"
{
    Properties
    {
        [Header(Texture)]
        [NoScaleOffset]_MainTex("MainTex", 2D) = "white" {}
        [NoScaleOffset]_FurMask("FurMask (RGB:Normal A:AO)", 2D) = "white" {}
        [NoScaleOffset]_FurDir("FurDir (RG:GrowDir BA:Flowmap)", 2D) = "white" {}
        [NoScaleOffset]_Noise("Opacity Noise", 2D) = "white" {}
        [NoScaleOffset]_Shift("Shift", 2D) = "white" {}

        [Header(Texture Settings)]
        _FurScale("FurMask Scale", float) = 10
        _NormalInt("Normal Intensity", Range(-5, 5)) = 1
        _FurDirInt("GrowDir Intensity", Range(0, 1)) = 1
        _NoiseScale("Noise Scale", float) = 1
        _NoiseOffset("Noise Offset", Range(-1, 1)) = 0
        _FlowmapSpeed("Flowmap Speed", float) = 1
        _FlowmapInt("Flowmap Intensity", Range(0, 2)) = 0.25

        [Space(20)]
        [Header(Shape)]
        _Thick("Fur Thickness", Range(0, 1)) = 0.1
        _ConePow("Cone Power", Range(0, 4)) = 1
        _FurMaxLayer("Max Layers", Range(1, 100)) = 20
        _OpacityPow("Opacity Pow", Range(0, 10)) = 1

        [Header(LOD)]
        _FurLODDistanceNear("LOD Distance Near", float) = 2
        _FurLODDistanceFar("LOD Distance Far", float) = 15

        [Space(20)]
        [Header(Color)]
        _BaseColContrast("Base Color Contrast", Range(0, 3)) = 1
        _RootCol("Root Color", Color) = (1,1,1,1)
        _AOCol("AO Color", Color) = (0,0,0,1)
        _RootPer("Root Percent", Range(0, 1)) = 0.5
        _AOInt("AO Intensity", Range(0, 5)) = 1
        _AOContrast("AO Contrast", Range(0, 10)) = 1

        [Space(20)]
        [Header(Diffuse)]
        _LightSmoothness("Light Smoothness", Range(0, 5)) = 1
        _LightOffset("Light Offset", Range(0, 5)) = 1

        [Space(20)]
        [Header(Fresnel)]
        _FresnelCol("Fresnel Color", Color) = (1,1,1,1)
        _FresnelInt("Fresnel Intensity", Range(0, 10)) = 0.5
        _FresnelPow("Fresnel Power", Range(0, 5)) = 2

        [Space(20)]
        [Header(SSS)]
        _SSSDistortion("SSS Distortion", Range(0, 5)) = 1
        _SSSPow("SSS Power", Range(0, 50)) = 1
        _SSSRange("SSS Range", Range(0, 10)) = 1
        _SSSInt("SSS Intensity", Range(0, 10)) = 1

        [Space(20)]
        [Header(Gravity)]
        _GravityDir("Gravity Direction", Vector) = (0, -1, 0, 1)

        [Space(20)]
        [Header(Wind)]
        _WindFreq("Wind Frequency", Vector) = (1, 0, 0, 1)
        _WindAmp("Wind Amplitude", Vector) = (0, 0, 0, 1)
        _WindOff("Wind Offset", float) = 0
        _BendInt("Bend Intensity", Range(0, 5)) = 1

    }
    SubShader
    {
        Tags
        {
            "RenderPipeline" = "UniversalRenderPipeline"
            "RenderType" = "Transparent"
            "Queue" = "Transparent"
        }

        Pass
        {
            Tags { "LightMode" = "FurShell" }
            Blend SrcAlpha OneMinusSrcAlpha

            Cull back
            ZWrite on

            HLSLPROGRAM

            #pragma vertex vert
            #pragma fragment frag
            
            // 阴影关键字
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS_CASCADE
            #pragma multi_compile _ _SHADOWS_SOFT

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl" 

            TEXTURE2D(_MainTex);    
            SAMPLER(sampler_MainTex);
            TEXTURE2D(_FurMask);    
            SAMPLER(sampler_FurMask);
            TEXTURE2D(_Noise);    
            SAMPLER(sampler_Noise);
            TEXTURE2D(_FurDir);    
            SAMPLER(sampler_FurDir);
            TEXTURE2D(_Shift);    
            SAMPLER(sampler_Shift);

            // 全局变量（由RendererFeature设置）
            float _Fur_Height01_GLB;
            float _FurTotalLayers_GLB;
            
            // 惯性延迟参数（由FurInertia组件设置）
            float3 _FurInertiaOffset;
            float _FurInertiaIntensity;

            CBUFFER_START(UnityPerMaterial)
                //贴图
                float4 _MainTex_ST;
                half _FurScale;
                half _NoiseScale;
                half _NoiseOffset;
                half _NormalInt;
                half _FurDirInt;
                half _FlowmapSpeed;
                half _FlowmapInt;

                //颜色
                half3 _RootCol;
                half3 _AOCol;
                half _RootPer;
                half _AOInt;
                half _AOContrast;
                half _BaseColContrast;
                half _OpacityPow;

                //漫反射
                half _LightSmoothness;
                half _LightOffset;
                
                //Fresnel
                half3 _FresnelCol;
                half _FresnelInt;
                half _FresnelPow;

                //形状
                half _ConePow;
                half _Thick;
                half _FurMaxLayer;

                //LOD
                half _FurLODDistanceNear;
                half _FurLODDistanceFar;

                //SSS
                half _SSSDistortion;
                half _SSSPow;
                half _SSSRange;
                half _SSSInt;
                
                //力
                half4 _GravityDir;
                half4 _WindFreq;
                half4 _WindAmp;
                half _WindOff;
                half _BendInt;
            CBUFFER_END

            struct a2v
            {
                float4 positionOS	: POSITION;
                float2 uv      : TEXCOORD0;
                float3 normalOS   : NORMAL;
                float4 tangentOS   : TANGENT;
            };

            struct v2f
            {
                float4 positionCS	    : SV_POSITION;
                float2 uv    : TEXCOORD0;
                float3 normalWS   : TEXCOORD1;
                float3 tangentWS   : TEXCOORD2;
                float3 bitangentWS   : TEXCOORD3;
                float3 positionWS    : TEXCOORD4;
                float4 shadowCoord    : TEXCOORD5;
                float dist : TEXCOORD6;
            };

            v2f vert(a2v i)
            {
                v2f o;

                //坐标
                float3 positionWS = TransformObjectToWorld(i.positionOS.xyz);
                o.normalWS = TransformObjectToWorldNormal(i.normalOS);
                o.tangentWS = TransformObjectToWorldDir(i.tangentOS.xyz);
                o.bitangentWS = cross(o.normalWS, o.tangentWS) * i.tangentOS.w;

                //UV
                float2 uv = TRANSFORM_TEX(i.uv, _MainTex);
                o.uv = uv;

                half4 furDirSample = SAMPLE_TEXTURE2D_LOD(_FurDir, sampler_FurDir, uv, 0);
                
                // RG通道解码为切线空间法线，控制毛发生长方向
                half3 furDirTS = half3(furDirSample.rg * 2.0h - 1.0h, 0);
                furDirTS.z = sqrt(max(0, 1.0h - dot(furDirTS.xy, furDirTS.xy))); // 重建Z分量
                half3x3 TBN = half3x3(normalize(o.tangentWS), normalize(o.bitangentWS), normalize(o.normalWS));
                half3 furDirWS = normalize(mul(furDirTS, TBN));
                
                // 混合原始法线和贴图法线
                half3 growDir = normalize(lerp(o.normalWS, furDirWS, _FurDirInt));
                
                // BA通道解码为flowmap方向，用于风力流动
                half2 flowmap = furDirSample.ba * 2.0h - 1.0h;
                half flowPhase = _Time.y * _FlowmapSpeed;

                //计算有效高度，用于弯曲因子（带LOD）
                o.dist = distance(positionWS, _WorldSpaceCameraPos);
                half lodFactor = saturate((o.dist - _FurLODDistanceNear) / max(_FurLODDistanceFar - _FurLODDistanceNear, 0.001h));
                half dynamicMaxLayer = lerp(_FurMaxLayer, 1, lodFactor);
                half layerScale = min(dynamicMaxLayer, _FurTotalLayers_GLB) / _FurTotalLayers_GLB;
                half effectiveHeight = _Fur_Height01_GLB / layerScale;
                
                // 重力弯曲（使用高度的平方，根部不动，顶部弯曲明显）
                half forceFactor = pow(effectiveHeight, _BendInt);
                half3 gravityForce = _GravityDir.xyz * forceFactor * _GravityDir.w;
                //风力弯曲（结合flowmap）
                half3 windAngle = _Time.w * _WindFreq.xyz * _WindFreq.w;
                half3 baseWindForce = forceFactor * _WindAmp * sin(windAngle + i.positionOS.xyz * _WindOff) * _WindAmp.w;
                // flowmap影响风力方向
                half3 flowmapWindForce = half3(flowmap * sin(flowPhase + effectiveHeight * 3.14159h), 0);
                flowmapWindForce = mul(TBN, flowmapWindForce) * forceFactor * _WindAmp.w * _FlowmapInt;
                half3 windForce = baseWindForce + flowmapWindForce;
                //惯性延迟力
                half3 inertiaForce = _FurInertiaOffset * forceFactor * _FurInertiaIntensity;
                
                half3 furDir = normalize(growDir + gravityForce + windForce + inertiaForce);
                
                // 法线方向生长
                positionWS += furDir * effectiveHeight * _Thick;
                o.positionCS = TransformWorldToHClip(positionWS);
                o.positionWS = positionWS;
                
                // 计算阴影坐标
                o.shadowCoord = TransformWorldToShadowCoord(positionWS);

                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                //计算有效高度，用于clip（带LOD）
                half lodFactor = saturate((i.dist - _FurLODDistanceNear) / max(_FurLODDistanceFar - _FurLODDistanceNear, 0.001h));
                lodFactor = pow(lodFactor, 0.3h);
                half dynamicMaxLayer = lerp(_FurMaxLayer, 1, lodFactor);
                half layerScale = min(dynamicMaxLayer, _FurTotalLayers_GLB) / _FurTotalLayers_GLB;
                half effectiveHeight = _Fur_Height01_GLB / layerScale;

                //采样
                half4 baseCol = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, i.uv);
                baseCol.rgb = (baseCol.rgb - 0.5h) * _BaseColContrast + 0.5h;
                half4 furMask = SAMPLE_TEXTURE2D(_FurMask, sampler_FurMask, i.uv * _FurScale);
                half Noise;
                if(lodFactor > 0.5h)
                    Noise = 0.5h;
                else
                    Noise = SAMPLE_TEXTURE2D(_Noise, sampler_Noise, i.uv * _NoiseScale).r;
                Noise = saturate(Noise + _NoiseOffset);

                //提前计算opacity并clip，跳过后续光照计算
                half height = saturate(furMask.a * furMask.a * 1.5h);
                half maxHeight = pow(height, _ConePow) * Noise;
                half coneMask = step(effectiveHeight, maxHeight);
                half heightOpacityAtten = pow(saturate(1.001h - effectiveHeight), _OpacityPow);
                half opacity = coneMask * heightOpacityAtten;
                clip(opacity - 0.001h);

                //向量
                half3 normalWS = normalize(i.normalWS);
                half3 tangentWS = normalize(i.tangentWS);
                half3 bitangentWS = normalize(i.bitangentWS);
                
                // 获取带阴影的主光源
                Light mainLight = GetMainLight(i.shadowCoord);
                half3 lightWS = mainLight.direction;
                half3 viewDirWS = normalize(GetWorldSpaceViewDir(i.positionWS));
                half shadowAtten = mainLight.shadowAttenuation;
                shadowAtten = lerp(0.2, 1, shadowAtten);

                //法线转换
                half3 normalTS = 2 * furMask.xyz - 1;
                normalTS.xy *= _NormalInt;
                half3x3 TBN = { normalize(tangentWS), normalize(bitangentWS), normalize(normalWS) };
                normalWS = normalize(mul(normalTS, TBN));

                //环境光（球谐采样）
                half3 ambientCol = SampleSH(normalWS);

                //AO
                half mainLuminance = dot(baseCol.rgb, half3(0.299, 0.587, 0.114));
                half ao_temp = saturate((mainLuminance * height - 0.5) * _AOContrast + 0.5);
                ao_temp = lerp(1, ao_temp, _AOInt);
                half aoCol = lerp(_AOCol * baseCol.rgb, _RootCol * baseCol.rgb, _RootPer);
                half ao = lerp(aoCol, 1, ao_temp);

                //光照
                half lambert = saturate(dot(normalWS, lightWS) + pow(max(_LightOffset * effectiveHeight, 0), _LightSmoothness));
                half halfLambert = dot(normalWS, lightWS) * 0.5 + 0.5;
                half3 directLight = mainLight.color * lambert * shadowAtten;
                half3 indirectLight = ambientCol * halfLambert;
                half3 diffuseCol = baseCol.rgb * (directLight + indirectLight) * ao;

                //Fresnel
                
                half3 fresnel = pow(1 - saturate(dot(normalWS, viewDirWS)), _FresnelPow) * _FresnelInt * _FresnelCol * ao_temp * lambert * mainLight.color * shadowAtten;

                //SSS
                half3 sssLight = -(lightWS + normalWS * _SSSDistortion);
                half LdotV = dot(sssLight, viewDirWS);
                half3 final_sss = saturate(pow(LdotV, _SSSPow) * _SSSRange) * ao_temp * mainLight.color * _SSSInt * baseCol.rgb;
                //混合
                half3 finalCol = diffuseCol + max(final_sss, fresnel);

                return half4(finalCol, opacity);
            }
            ENDHLSL
        }

        // 阴影投射Pass
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
            };

            Varyings vert (Attributes v)
            {
                Varyings o;
                float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
                float3 normalWS = TransformObjectToWorldNormal(v.normalOS);

                // 应用阴影bias，防止shadow acne
                float4 positionCS = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, _MainLightPosition));

                #if UNITY_REVERSED_Z
                    positionCS.z = min(positionCS.z, positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #else
                    positionCS.z = max(positionCS.z, positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #endif

                o.positionCS = positionCS;
                return o;
            }

            half4 frag (Varyings i) : SV_Target
            {
                return 0;
            }
            ENDHLSL
        }
    }
}