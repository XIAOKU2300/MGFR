// ------------------------------------------------------------------
            // PCF Filtering (Tent) - 使用 Unity Core 标准实现
            // ------------------------------------------------------------------

            #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Shadow/ShadowSamplingTent.hlsl"

            TEXTURE2D(_ShadowRampTex);
            SAMPLER(sampler_ShadowRampTex);
            TEXTURE2D_X(_PerObjectTransparentDepthTexture);
            float _UseShadowRamp;

            /// <summary>
            /// 使用 Tent Filter 进行 PCF 阴影采样
            /// 支持 _PCF_LOW (3x3), _PCF_HIGH (7x7), 默认为 5x5
            /// </summary>
            real SampleShadowPCF_Tent(float2 uv, float depth, float2 minCoord, float2 maxCoord)
            {
                real2 invShadowMapSize = rcp(_PerObjectShadowAtlasSize.xy);
                real4 shadowMapTexelSize = real4(invShadowMapSize.x, invShadowMapSize.y, _PerObjectShadowAtlasSize.x, _PerObjectShadowAtlasSize.y);

                // 限制采样范围在 Atlas 的当前 Tile 内，防止 Mipmap Bleeding
                real2 cMin = minCoord + invShadowMapSize * 0.5;
                real2 cMax = maxCoord - invShadowMapSize * 0.5;

                real attenuation = real(1.0);

                #if defined(_PCF_LOW)
                    // 3x3 Tent Filter (4 fetches)
                    real fetchesWeights[4];
                    real2 fetchesUV[4];
                    SampleShadow_ComputeSamples_Tent_3x3(shadowMapTexelSize, uv, fetchesWeights, fetchesUV);

                    real sumW = 0;
                    real sumS = 0;
                    [unroll]
                    for (int i = 0; i < 4; i++)
                    {
                        real2 sampleCoord = fetchesUV[i];
                        if (!(any(sampleCoord < cMin) || any(sampleCoord > cMax)))
                        {
                            real s = SAMPLE_TEXTURE2D_SHADOW(_PerObjectShadowmapTexture, sampler_LinearClampCompare, float3(sampleCoord, depth));
                            sumS += fetchesWeights[i] * s;
                            sumW += fetchesWeights[i];
                        }
                    }
                    attenuation = sumW > 0 ? sumS / sumW : 1.0;

                #elif defined(_PCF_HIGH)
                    // 7x7 Tent Filter (16 fetches)
                    real fetchesWeights[16];
                    real2 fetchesUV[16];
                    SampleShadow_ComputeSamples_Tent_7x7(shadowMapTexelSize, uv, fetchesWeights, fetchesUV);

                    real sumW = 0;
                    real sumS = 0;
                    [unroll]
                    for (int i = 0; i < 16; i++)
                    {
                        real2 sampleCoord = fetchesUV[i];
                        if (!(any(sampleCoord < cMin) || any(sampleCoord > cMax)))
                        {
                            real s = SAMPLE_TEXTURE2D_SHADOW(_PerObjectShadowmapTexture, sampler_LinearClampCompare, float3(sampleCoord, depth));
                            sumS += fetchesWeights[i] * s;
                            sumW += fetchesWeights[i];
                        }
                    }
                    attenuation = sumW > 0 ? sumS / sumW : 1.0;


                #else
                    // 5x5 Tent Filter (9 fetches)
                    real fetchesWeights[9];
                    real2 fetchesUV[9];
                    SampleShadow_ComputeSamples_Tent_5x5(shadowMapTexelSize, uv, fetchesWeights, fetchesUV);

                    real sumW = 0;
                    real sumS = 0;
                    [unroll]
                    for (int i = 0; i < 9; i++)
                    {
                        real2 sampleCoord = fetchesUV[i];
                        if (!(any(sampleCoord < cMin) || any(sampleCoord > cMax)))
                        {
                            real s = SAMPLE_TEXTURE2D_SHADOW(_PerObjectShadowmapTexture, sampler_LinearClampCompare, float3(sampleCoord, depth));
                            sumS += fetchesWeights[i] * s;
                            sumW += fetchesWeights[i];
                        }
                    }
                    attenuation = sumW > 0 ? sumS / sumW : 1.0;
                #endif

                return attenuation;
            }

            /// <summary>
            /// 采样渐变色带 (Ramp)
            /// 使用阴影衰减值作为 U 坐标
            /// </summary>
            half3 SampleShadowRamp(half shadow)
            {
                if (_UseShadowRamp > 0.5)
                {
                    return SAMPLE_TEXTURE2D(_ShadowRampTex, sampler_ShadowRampTex, float2(shadow, 0.5)).rgb;
                }
                else
                {
                    return shadow.xxx;
                }
            }

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float4 screenPos : TEXCOORD0;
            };

            Varyings VolumeVert(Attributes input)
            {
                Varyings output;
                output.positionCS = TransformObjectToHClip(input.positionOS.xyz);
                output.screenPos = ComputeScreenPos(output.positionCS);
                return output;
            }

            /// <summary>
            /// 体积盒投影片元着色器
            /// 1. 重建世界空间坐标
            /// 2. 投影到体积盒局部空间进行裁剪
            /// 3. 投影到阴影空间进行采样
            /// 4. 应用 Ramp 和强度调节
            /// </summary>
            half4 VolumeFrag(Varyings input) : SV_Target
            {
                float2 screenUV = input.screenPos.xy / input.screenPos.w;
                float sceneDepth = SampleSceneDepth(screenUV);
                float transparentDepth = SAMPLE_TEXTURE2D_X(_PerObjectTransparentDepthTexture, sampler_PointClamp, UnityStereoTransformScreenSpaceTex(screenUV)).r;
                #if UNITY_REVERSED_Z
                float depth = max(sceneDepth, transparentDepth);
                #else
                float depth = min(sceneDepth, transparentDepth);
                #endif

                // 重建世界空间坐标 (UNITY_MATRIX_I_VP 在 C# 中手动设置)
                float3 worldPos = ComputeWorldSpacePosition(screenUV, depth, UNITY_MATRIX_I_VP);

                // 核心逻辑：利用体积盒局部坐标进行范围裁剪
                float4 positionSHCS = mul(_VolumeWorldToShadowClip, float4(worldPos, 1.0));
                positionSHCS.xyz /= positionSHCS.w;
                
                float3 clipDist = 1.001 - abs(positionSHCS.xyz);
                clip(min(clipDist.x, min(clipDist.y, clipDist.z)));

                // 投影回 ShadowMap 坐标
                float4 shadowCoord = mul(_VolumeWorldToShadow, float4(worldPos, 1.0));
                shadowCoord.xyz /= shadowCoord.w;

                float2 minCoord = _VolumeUvScaleOffset.zw;
                float2 maxCoord = _VolumeUvScaleOffset.xy + _VolumeUvScaleOffset.zw;

                float softShadowEnabled = _PerObjectShadowParams.z;

                float shadow = 1.0;
                if (softShadowEnabled > 0.5)
                {
                    shadow = SampleShadowPCF_Tent(shadowCoord.xy, shadowCoord.z, minCoord, maxCoord);
                }
                else
                {
                    shadow = SAMPLE_TEXTURE2D_SHADOW(_PerObjectShadowmapTexture, sampler_LinearClampCompare, float3(shadowCoord.xy, shadowCoord.z));
                }

                // 处理彩色渐变逻辑
                half3 shadowColor = SampleShadowRamp(shadow);
                
                if (_UseShadowRamp > 0.5)
                {
                    // 在线性衰减和彩色色带间根据强度插值
                    shadowColor = lerp(shadow.xxx, shadowColor, _PerObjectShadowParams.y);
                }

                // 应用最终阴影强度 (x 分量)
                half3 finalColor = lerp(half3(1.0, 1.0, 1.0), shadowColor, _PerObjectShadowParams.x);

                return half4(finalColor, 1.0);
            }
