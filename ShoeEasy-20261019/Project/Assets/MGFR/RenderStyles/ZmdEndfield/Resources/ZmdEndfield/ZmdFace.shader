Shader "MGFR/ZmdEndfield/Face"
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
        [Header(Mode)]
        [Toggle(_SIMPLE_MODE)] _SimpleMode ("Simple Mode", Float) = 0
        
        [Header(Map)]
        _BaseColor ("BaseColor", 2D) = "white" {}
        _ColorMask ("ColorMask", 2D) = "white" {}
        _LipSpecMask ("LipSpecMask", 2D) = "white" {}
        _SDF ("SDF", 2D) = "white" {}
        _DiffuseRamp ("Diffuse Ramp (NPR)", 2D) = "white" {}
        [Header(Color)]
        _SecondColor ("Second Color", Color) = (1, 1, 1, 1)
        _DarkColor ("DarkColor", Color) = (0.5, 0.5, 0.5, 1)
        _RampStrength ("NPR Ramp Strength", Range(0, 1)) = 1.0
        
        [Header(Shadow)]
        _ShadowColor ("Shadow Color", Color) = (0.5, 0.5, 0.5, 1)
        _ShadowStrength ("Shadow Strength", Range(0, 1)) = 1.0

        [Header(SDF)]
        _SoftShadow ("_SoftShadow", range(0, 1)) = 0.2
        [Header(Specular)]
        _SpecularColor ("Specular Color", Color) = (1, 1, 1, 1)
        _SpecularIntensity ("Specular Intensity", Range(0, 8)) = 4
        [Header(AO)]
        _AO_Offset ("AO Offset", range(-1, 1)) = 0
        [Header(Outline)]
        _OutLine ("Outline Width", range(0, 1)) = 1
        _OutLineColor ("Outline Color", Color) = (1, 1, 1, 1)
        [HideInInspector] _HeadForward ("HeadForward", Vector) = (0, 0, 1, 0)
        [HideInInspector] _HeadRight ("HeadRight", Vector) = (1, 0, 0, 0)
        [HideInInspector] _HeadUp ("HeadUp", Vector) = (0, 1, 0, 0)
        [HideInInspector] _StencilRef("Stencil Ref", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType"="Opaque"  }
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

            
            Cull [_Cull] ZWrite [_ZWrite] Blend [_SrcBlend] [_DstBlend]
            HLSLPROGRAM
#pragma target 3.5
#pragma multi_compile_instancing
            #pragma vertex vert
            #pragma fragment frag
            
            
            #pragma multi_compile_fwdbase
            #pragma shader_feature_local _SIMPLE_MODE

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
                float4 color : COLOR;
            };

            struct Varyings
            {
 UNITY_VERTEX_OUTPUT_STEREO
                float2 uv : TEXCOORD0;
                float4 positionCS : SV_POSITION;
                float3 normalWS : TEXCOORD1;
                float4 shadowCoord : TEXCOORD2;
                float3 positionWS : TEXCOORD3;
                float4 perObjectShadowCoord : TEXCOORD4;
                float4 color : COLOR;
            };

            TEXTURE2D(_BaseColor);
            SAMPLER(sampler_BaseColor);
            TEXTURE2D(_ColorMask);
            SAMPLER(sampler_ColorMask);
            TEXTURE2D(_SDF);
            SAMPLER(sampler_SDF);
            TEXTURE2D(_LipSpecMask);
            SAMPLER(sampler_LipSpecMask);
            TEXTURE2D(_DiffuseRamp);
            SAMPLER(sampler_DiffuseRamp);

            float _PerObjectShadowEnabled;

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor_ST;
                half4 _Color;
                half4 _SecondColor;
                half4 _DarkColor;
                half _RampStrength;
                half4 _ShadowColor;
                half _ShadowStrength;
                half _SoftShadow;
                half4 _SpecularColor;
                half _SpecularIntensity;
                half _AO_Offset;
                half3 _HeadForward;
                half3 _HeadRight;
                half3 _HeadUp;
            CBUFFER_END

            #define S_CHAR_FORWARD_PASS
            #include "ZmdCharUtils.cginc"

            Varyings vert (Attributes v)
            {
                Varyings o;
 UNITY_SETUP_INSTANCE_ID(v); UNITY_INITIALIZE_OUTPUT(Varyings,o); UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                VertexPositionInputs vertexInput = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = vertexInput.positionCS;
                o.positionWS = vertexInput.positionWS;
                o.uv = TRANSFORM_TEX(v.uv, _BaseColor);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.shadowCoord = GetShadowCoord(vertexInput);
                o.perObjectShadowCoord = ComputeScreenPos(vertexInput.positionCS);
                o.color = v.color;
                return o;
            }

            half4 frag (Varyings i) : SV_Target
            {
 UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                //输入
                half4 baseMap = SAMPLE_TEXTURE2D(_BaseColor, sampler_BaseColor, i.uv)*_Color;
                half4 sdfRight = SAMPLE_TEXTURE2D(_SDF, sampler_SDF, i.uv);
                half4 sdfLeft = SAMPLE_TEXTURE2D(_SDF, sampler_SDF, float2((1.0 - i.uv.x), i.uv.y));
                
                #ifndef _SIMPLE_MODE
                half4 colorMask = SAMPLE_TEXTURE2D(_ColorMask, sampler_ColorMask, i.uv);
                half ao = saturate(baseMap.a + _AO_Offset);
                half secondColorMask = max(colorMask.r , colorMask.g);
                half jawShadow = colorMask.g;
                half selfShadowMask = colorMask.b;
                half specMask = colorMask.a;
                #endif
                
                //向量
                half3 normalWS = normalize(i.normalWS);
                half3 viewDirWS = normalize(GetWorldSpaceViewDir(i.positionWS));
                half3 headUpDir = normalize(_HeadUp);
                half3 headRightDir = normalize(_HeadRight);
                half3 headForwardDir = normalize(_HeadForward);
                Light mainLight = GetMainLight(i.shadowCoord);

                //环境光
                half3 ambient = SampleSH(half3(0, 0, 0));
                
                #ifndef _SIMPLE_MODE
                // 阴影
                half3 screenShadow = saturate(SamplePerObjectScreenSpaceShadowmap(i.perObjectShadowCoord));
                
                half finalShadowStrength = _Global_ShadowStrength * _ShadowStrength;
                half3 coloredShadow = lerp(_ShadowColor.rgb, half3(1.0, 1.0, 1.0), screenShadow.x);
                half3 perObjectShadow = lerp(half3(1.0, 1.0, 1.0), screenShadow, finalShadowStrength) * coloredShadow;
                
                half viewSdfDot = dot(viewDirWS, headForwardDir);
                half faceViewBlend = smoothstep(0.0, 0.5, viewSdfDot); 
                half blendedSelfShadowMask = lerp((1 - selfShadowMask), (1 - jawShadow), faceViewBlend);
                half unityShadow = lerp(1.0, mainLight.shadowAttenuation, finalShadowStrength);

                half3 shadowAtten = max(perObjectShadow, blendedSelfShadowMask);

                //直接光漫反射
                half3 secondCol = baseMap.rgb * _SecondColor.rgb;
                half3 diffuse = lerp(baseMap.rgb, secondCol, secondColorMask) * _DarkColor.rgb;
                #else
                half unityShadow = mainLight.shadowAttenuation;
                half3 diffuse = baseMap.rgb * _DarkColor.rgb;
                #endif

                // 区分暗部和亮部基础光照
                half3 diffuseDark = diffuse * ambient * 1.5;
                half3 baseDiffuseLight = diffuse * mainLight.color;

                // ================= SDF 光照 =================
                half3 lightOnHeadPlane = mainLight.direction - headUpDir * dot(mainLight.direction, headUpDir);
                half planeLenSq = max(dot(lightOnHeadPlane, lightOnHeadPlane), 1e-4);
                half3 headPlaneLightDir = lightOnHeadPlane * rsqrt(planeLenSq);

				half sdf_dot = dot(headPlaneLightDir, headForwardDir);
                half LOR = step(dot(headPlaneLightDir, headRightDir), 0.0);
				half softShadow = _SoftShadow * 0.5;
                half4 activeSdf = lerp(sdfRight, sdfLeft, LOR);

				half frontShadow = smoothstep((sdf_dot + softShadow), max((sdf_dot - softShadow), 0.0), (1.0 - activeSdf.g));
				half dotRemap = saturate(sdf_dot + 1.0);
				half backShadow = smoothstep(min((dotRemap + softShadow), 1.0), (dotRemap - softShadow), (1.0 - activeSdf.r));

                half channelBlend = smoothstep(softShadow, -softShadow, sdf_dot);
				half sdfShaodw = min(saturate(lerp(frontShadow, backShadow, channelBlend)), unityShadow);
                half3 sdfRamp = SAMPLE_TEXTURE2D(_DiffuseRamp, sampler_DiffuseRamp, half2(sdfShaodw, 0.5)).rgb;

                // 计算SDF模式的亮部              
                half3 baseSdfLight = baseDiffuseLight * sdfShaodw;
                half3 softLightSdfRamp = BlendSoftLight(baseSdfLight, sdfRamp);
                half3 sdfLight = lerp(baseSdfLight, softLightSdfRamp, _RampStrength);

                #ifndef _SIMPLE_MODE
                // ================= 兰伯特光照 =================
                half NdotL = dot(normalWS, mainLight.direction);
                half halfLambert = min(saturate((NdotL * 0.5 + 0.5) + 0.2), unityShadow);
                half3 ramp = SAMPLE_TEXTURE2D(_DiffuseRamp, sampler_DiffuseRamp, half2(halfLambert, 0.5)).rgb;

                // 计算兰伯特模式的亮部              
                half3 baseLambertLight = baseDiffuseLight * halfLambert;
                half3 softLightRamp = BlendSoftLight(baseLambertLight, ramp);
                half3 lambertLight = lerp(baseLambertLight, softLightRamp, _RampStrength);

                // ================= 混合光照 =================
                // 根据jawShadow混合SDF和兰伯特光照
                half3 diffuseLight = lerp(sdfLight, lambertLight, jawShadow);

                half3 final_diff = max(diffuseDark, diffuseLight) * ao * shadowAtten;

                //高光
                half halfMask = step(i.uv.x, 0.5);
                half lightHM = lerp(halfMask, 1 - halfMask, LOR);
                half NdotV = max(0, dot(headForwardDir, viewDirWS));
                half fresnel = _SpecularIntensity * saturate(NdotV - 0.75);
                half lipSpecMaskOffset = dot(viewDirWS, headRightDir) * 0.05;
                half2 lipSpecMaskUV = half2(i.uv.x + lipSpecMaskOffset, i.uv.y);
                half lipSpecMask = SAMPLE_TEXTURE2D(_LipSpecMask, sampler_LipSpecMask, lipSpecMaskUV).r;
                lipSpecMask *= 1 - step(sdf_dot, 0);
                specMask = specMask * lightHM * fresnel * saturate(sdf_dot) + lipSpecMask;
                half3 final_spec = _SpecularColor.rgb * mainLight.color * specMask * shadowAtten;

                half3 finalColor = final_diff + final_spec;
                #else
                half3 finalColor = max(diffuseDark, sdfLight);
                #endif

                //return half4(lerp(sdfRamp, ramp, jawShadow) * shadowAtten, 1.0);
                return half4(ZmdFinish(finalColor), 1.0);
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
            #pragma vertex SChar_OutlineVert
            #pragma fragment SChar_OutlineFrag

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
            #pragma multi_compile_shadowcaster
            #pragma vertex SChar_ShadowVert
            #pragma fragment SChar_ShadowFrag

            #include "ZmdCharUtils.cginc"
            ENDHLSL
        }
    }
}
