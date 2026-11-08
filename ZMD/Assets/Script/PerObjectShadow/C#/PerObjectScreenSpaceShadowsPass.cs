using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace UnityEngine.Rendering.Universal
{
    /// <summary>
    /// 第二阶段：屏幕空间阴影计算 Pass
    /// 利用体积盒 (Volume Box) 重建世界坐标，采样 ShadowMap 并输出到屏幕空间彩色贴图
    /// </summary>
    public class PerObjectScreenSpaceShadowsPass : ScriptableRenderPass
    {
        private static readonly ProfilingSampler s_ProfilingSampler = new ProfilingSampler("PerObject ScreenSpace Shadows");
        
        // Shader 属性映射
        private static readonly int s_ShadowMapID = Shader.PropertyToID("_PerObjectShadowmapTexture");
        private static readonly int s_ShadowParamsID = Shader.PropertyToID("_PerObjectShadowParams");
        private static readonly int s_ShadowAtlasSizeID = Shader.PropertyToID("_PerObjectShadowAtlasSize");
        private static readonly int s_ScreenSpaceShadowMapID = Shader.PropertyToID("_PerObjectScreenSpaceShadowMap");
        
        // 体积投影矩阵属性
        private static readonly int s_VolumeWorldToShadowID = Shader.PropertyToID("_VolumeWorldToShadow");
        private static readonly int s_VolumeWorldToShadowClipID = Shader.PropertyToID("_VolumeWorldToShadowClip");
        private static readonly int s_VolumeUvScaleOffsetID = Shader.PropertyToID("_VolumeUvScaleOffset");
        private static readonly int s_ShadowRampTexID = Shader.PropertyToID("_ShadowRampTex");
        private static readonly int s_UseShadowRampID = Shader.PropertyToID("_UseShadowRamp");
        private static readonly int s_PerObjectShadowEnabledID = Shader.PropertyToID("_PerObjectShadowEnabled");

        // PCF 变体关键字
        private static readonly string k_PCFLowKeyword = "_PCF_LOW";
        private static readonly string k_PCFMediumKeyword = "_PCF_MEDIUM";
        private static readonly string k_PCFHighKeyword = "_PCF_HIGH";
        
        private PerObjectShadowFeature m_Feature;
        private RTHandle m_MainShadowMapTexture;       
        private RTHandle m_VirtualShadowMapTexture;    
        private bool m_EnableVirtualLight;
        private List<PerObjectShadowData> m_ShadowDataList; 
        private int m_ValidObjectCount;                
        private Vector2Int m_EnvironmentShadowMapResolution;
        private int m_EnvironmentTileResolution;
        private Vector2Int m_SelfShadowMapResolution;
        private int m_SelfTileResolution;
        
        private RTHandle m_ScreenSpaceShadowMapTexture;         // 存储最终生成的彩色阴影图
        private RTHandle m_ResolvedScreenSpaceShadowMapTexture;  // MSAA 解析后的纹理
        
        private Material m_ShadowMaterial;                      // 核心渲染材质
        private readonly Dictionary<int, Material> m_SelfStencilMaterials = new Dictionary<int, Material>();// 键值表，用于存储自阴影材质，键为模板值，值为材质
        
        public PerObjectScreenSpaceShadowsPass(PerObjectShadowFeature feature)
        {
            m_Feature = feature;
            
            Shader shader = Shader.Find("Hidden/PerObjectShadowCaster");
            if (shader != null)
                m_ShadowMaterial = new Material(shader);
        }
        
        /// <summary>
        /// 接收第一阶段的渲染数据
        /// </summary>
        public bool Setup(RTHandle mainShadowMap, RTHandle virtualShadowMap, List<PerObjectShadowData> shadowDataList, 
            int validObjectCount, Vector2Int environmentShadowMapResolution, int environmentTileResolution,
            Vector2Int selfShadowMapResolution, int selfTileResolution, bool enableVirtualLight)
        {
            m_MainShadowMapTexture = mainShadowMap;
            m_VirtualShadowMapTexture = virtualShadowMap;
            m_EnableVirtualLight = enableVirtualLight;
            m_ShadowDataList = shadowDataList;
            m_ValidObjectCount = validObjectCount;
            m_EnvironmentShadowMapResolution = environmentShadowMapResolution;
            m_EnvironmentTileResolution = environmentTileResolution;
            m_SelfShadowMapResolution = selfShadowMapResolution;
            m_SelfTileResolution = selfTileResolution;
            
            ConfigureInput(ScriptableRenderPassInput.Depth); // 必须依赖深度图重建坐标
            
            return m_MainShadowMapTexture != null && m_ValidObjectCount > 0;
        }
        
        /// <summary>
        /// 配置渲染目标
        /// </summary>
        public override void OnCameraSetup(CommandBuffer cmd, ref RenderingData renderingData)
        {
            // 确保屏幕空间阴影纹理已创建且尺寸正确
            RenderTextureDescriptor descriptor = renderingData.cameraData.cameraTargetDescriptor;
            descriptor.colorFormat = RenderTextureFormat.ARGB32; // 改为支持彩色
            descriptor.depthBufferBits = 0; // 我们使用相机的深度缓冲，不需要自己的
            
            // 为了支持 Stencil，阴影纹理的 MSAA 必须与相机匹配
            int cameraMsaaSamples = renderingData.cameraData.cameraTargetDescriptor.msaaSamples;
            descriptor.msaaSamples = cameraMsaaSamples;
            descriptor.useMipMap = false;
            descriptor.autoGenerateMips = false;

            if (RenderingUtils.ReAllocateIfNeeded(ref m_ScreenSpaceShadowMapTexture, descriptor, FilterMode.Bilinear, TextureWrapMode.Clamp, name: "_PerObjectScreenSpaceShadowMap"))
            {
                // 纹理重新分配了
            }

            // 如果开启了 MSAA，我们需要一个降采样的纹理供后续 Shader 采样，因为开启了msaa的相机深度缓冲是多倍采样，包含多个深度值和模板值，而阴影纹理只有1x采样
            if (cameraMsaaSamples > 1)
            {
                RenderTextureDescriptor resolvedDescriptor = descriptor;
                resolvedDescriptor.msaaSamples = 1;
                if (RenderingUtils.ReAllocateIfNeeded(ref m_ResolvedScreenSpaceShadowMapTexture, resolvedDescriptor, FilterMode.Bilinear, TextureWrapMode.Clamp, name: "_PerObjectScreenSpaceShadowMap_Resolved"))
                {
                    // Resolved 纹理重新分配了
                }
            }
            else
            {
                m_ResolvedScreenSpaceShadowMapTexture?.Release();
                m_ResolvedScreenSpaceShadowMapTexture = null;
            }

            // 设置渲染目标：颜色缓冲为屏幕空间阴影纹理，深度缓冲为相机当前的深度缓冲（包含 Stencil）
            ConfigureTarget(m_ScreenSpaceShadowMapTexture, renderingData.cameraData.renderer.cameraDepthTargetHandle);
        }

        public override void Configure(CommandBuffer cmd, RenderTextureDescriptor cameraTextureDescriptor)
        {
            ConfigureClear(ClearFlag.None, Color.white);
        }
        
        public override void Execute(ScriptableRenderContext context, ref RenderingData renderingData)
        {
            if (m_ShadowMaterial == null || m_MainShadowMapTexture == null || m_ValidObjectCount == 0 || m_ScreenSpaceShadowMapTexture == null)
                return;
            
            CommandBuffer cmd = CommandBufferPool.Get("PerObjectScreenSpaceShadow");
            
            using (new ProfilingScope(cmd, s_ProfilingSampler))
            {
                // 保险，确保在没有阴影产生时，系统能退回到无阴影状态
                cmd.SetGlobalFloat(s_PerObjectShadowEnabledID, 0.0f);
                cmd.SetGlobalTexture(s_ScreenSpaceShadowMapID, Texture2D.whiteTexture);

                bool didDraw = false;
                // 获取相机深度图
                RTHandle cameraDepthTarget = renderingData.cameraData.renderer.cameraDepthTargetHandle;
                
                // 始终绑定深度缓冲以支持 Stencil 和 ZTest
                // 现在的 m_ScreenSpaceShadowMapTexture MSAA 已与 cameraDepthTarget 匹配
                cmd.SetRenderTarget(m_ScreenSpaceShadowMapTexture, cameraDepthTarget);
                
                cmd.ClearRenderTarget(false, true, Color.white);

                // 显式计算并设置逆 VP 矩阵，确保在各平台/视图下重建世界坐标正确，将屏幕上的点转化到世界坐标
                Matrix4x4 viewMatrix = renderingData.cameraData.GetViewMatrix();
                Matrix4x4 projectionMatrix = renderingData.cameraData.GetProjectionMatrix();
                Matrix4x4 gpuVP = GL.GetGPUProjectionMatrix(projectionMatrix, false) * viewMatrix;
                cmd.SetGlobalMatrix("UNITY_MATRIX_I_VP", gpuVP.inverse);

                // 获取体积投影 Pass 的实际索引
                int envVolumePassIndex = m_ShadowMaterial.FindPass("PerObjectShadowVolume_Env");
                int envAllVolumePassIndex = m_ShadowMaterial.FindPass("PerObjectShadowVolume_EnvAll");
                int selfVolumePassIndex = m_ShadowMaterial.FindPass("PerObjectShadowVolume_Self");

                // 如果找不到 Pass，说明 Shader 编译失败或版本不对，跳过绘制以避免 CommandBuffer 报错
                if (envVolumePassIndex == -1 || envAllVolumePassIndex == -1 || selfVolumePassIndex == -1)
                {
                    Debug.LogError("PerObjectShadow: 找不到必要的 Shader Pass (PerObjectShadowVolume_Env / PerObjectShadowVolume_EnvAll / PerObjectShadowVolume_Self)，请检查 Hidden/PerObjectShadowCaster 是否编译成功");
                    return;
                }

                bool useSelfShadow = m_Feature.selfShadow.enabled && m_EnableVirtualLight && m_VirtualShadowMapTexture != null;

                // --- 体积投影绘制 ---
                // 遍历每个阴影对象，绘制其对应的体积盒
                // 环境投影
                if (m_Feature.environmentShadow.enabled)
                {
                    didDraw = true;
                    m_Feature.environmentShadow.BakeGradient();//再次调用确保万无一失，在颜色没有变化的时候，开销微乎其微
                    
                    Vector4 environmentAtlasSize = new Vector4(m_EnvironmentShadowMapResolution.x, m_EnvironmentShadowMapResolution.y, m_EnvironmentTileResolution, m_EnvironmentTileResolution);
                    cmd.SetGlobalVector(s_ShadowAtlasSizeID, environmentAtlasSize);
                    ApplyShadowParams(cmd, m_Feature.environmentShadow.shadowType, m_Feature.environmentShadow.useRamp, m_Feature.environmentShadow.bakedRampTex, m_Feature.environmentShadow.rampIntensity);
                    UpdatePCFKeywords(cmd, m_Feature.environmentShadow.pcfQuality);//更新关键字，高效管理shader变体

                    int volumePassIndex = useSelfShadow ? envVolumePassIndex : envAllVolumePassIndex;//自阴影开启则使用自阴影，自阴影关闭则角色和环境都使用环境投影
                    foreach (var shadowData in m_ShadowDataList)
                    {
                        if (shadowData.isCulled || shadowData.projector == null) continue;

                        var mainSlice = shadowData.mainSliceData;
                        cmd.SetGlobalTexture(s_ShadowMapID, m_MainShadowMapTexture.nameID);
                        cmd.SetGlobalMatrix(s_VolumeWorldToShadowID, mainSlice.shadowTransform);
                        cmd.SetGlobalMatrix(s_VolumeWorldToShadowClipID, (mainSlice.projectionMatrix * mainSlice.viewMatrix));
                        cmd.SetGlobalVector(s_VolumeUvScaleOffsetID, mainSlice.uvScaleOffset);
                        cmd.DrawMesh(PerObjectShadowUtils.shadowProjectorMesh, mainSlice.shadowToWorldMatrix, m_ShadowMaterial, 0, volumePassIndex);
                    }
                }
                // 自阴影投影
                if (m_Feature.selfShadow.enabled && m_EnableVirtualLight && m_VirtualShadowMapTexture != null)
                {
                    didDraw = true;
                    m_Feature.selfShadow.BakeGradient();

                    Vector4 selfAtlasSize = new Vector4(m_SelfShadowMapResolution.x, m_SelfShadowMapResolution.y, m_SelfTileResolution, m_SelfTileResolution);
                    cmd.SetGlobalVector(s_ShadowAtlasSizeID, selfAtlasSize);
                    ApplyShadowParams(cmd, m_Feature.selfShadow.shadowType, m_Feature.selfShadow.useRamp, m_Feature.selfShadow.bakedRampTex, m_Feature.selfShadow.rampIntensity);
                    UpdatePCFKeywords(cmd, m_Feature.selfShadow.pcfQuality);

                    foreach (var shadowData in m_ShadowDataList)
                    {
                        if (shadowData.isCulled || shadowData.projector == null) continue;

                        var virtualSlice = shadowData.virtualSliceData;
                        int stencilRef = shadowData.projector.stencilRef;
                        // 赋值键值表，如果不存在则创建新材质，用于每个角色只接收自己的阴影
                        if (!m_SelfStencilMaterials.TryGetValue(stencilRef, out var selfMat) || selfMat == null)
                        {
                            selfMat = new Material(m_ShadowMaterial);
                            selfMat.hideFlags = HideFlags.DontSave;
                            selfMat.SetFloat("_StencilRef", stencilRef);
                            m_SelfStencilMaterials[stencilRef] = selfMat;
                        }

                        cmd.SetGlobalTexture(s_ShadowMapID, m_VirtualShadowMapTexture.nameID);
                        cmd.SetGlobalMatrix(s_VolumeWorldToShadowID, virtualSlice.shadowTransform);
                        cmd.SetGlobalMatrix(s_VolumeWorldToShadowClipID, (virtualSlice.projectionMatrix * virtualSlice.viewMatrix));
                        cmd.SetGlobalVector(s_VolumeUvScaleOffsetID, virtualSlice.uvScaleOffset);
                        cmd.DrawMesh(PerObjectShadowUtils.shadowProjectorMesh, virtualSlice.shadowToWorldMatrix, selfMat, 0, selfVolumePassIndex);
                    }
                }



                // 如果开启了 MSAA，需要降采样到非 MSAA 纹理才能被后续材质正确采样
                if (m_ResolvedScreenSpaceShadowMapTexture != null)
                {
                    cmd.ResolveAntiAliasedSurface(m_ScreenSpaceShadowMapTexture, m_ResolvedScreenSpaceShadowMapTexture);
                    cmd.SetGlobalTexture(s_ScreenSpaceShadowMapID, m_ResolvedScreenSpaceShadowMapTexture.nameID);
                }
                else
                {
                    cmd.SetGlobalTexture(s_ScreenSpaceShadowMapID, m_ScreenSpaceShadowMapTexture.nameID);
                }

                cmd.SetGlobalFloat(s_PerObjectShadowEnabledID, didDraw ? 1.0f : 0.0f);//1.0则走perobjectshadow路线，0.0则走unity内置阴影路线
            }
            
            context.ExecuteCommandBuffer(cmd);
            CommandBufferPool.Release(cmd);
        }

        private PerObjectShadowFeature.PCFQuality? m_CurrentPCFQuality = null;//让PCFQuality可空使得UpdatePCFKeywords完整运行一遍
        // PCF关键字更新方法
        private void UpdatePCFKeywords(CommandBuffer cmd, PerObjectShadowFeature.PCFQuality pcfQuality)
        {
            if (m_CurrentPCFQuality == pcfQuality)
                return;

            cmd.DisableShaderKeyword(k_PCFLowKeyword);
            cmd.DisableShaderKeyword(k_PCFMediumKeyword);
            cmd.DisableShaderKeyword(k_PCFHighKeyword);

            switch (pcfQuality)
            {
                case PerObjectShadowFeature.PCFQuality.Low_3x3:
                    cmd.EnableShaderKeyword(k_PCFLowKeyword);
                    break;
                case PerObjectShadowFeature.PCFQuality.Medium_5x5:
                    cmd.EnableShaderKeyword(k_PCFMediumKeyword);
                    break;
                case PerObjectShadowFeature.PCFQuality.High_7x7:
                    cmd.EnableShaderKeyword(k_PCFHighKeyword);
                    break;
            }
            m_CurrentPCFQuality = pcfQuality;
        }
        // 赋予阴影参数值
        private void ApplyShadowParams(CommandBuffer cmd, PerObjectShadowFeature.ShadowType shadowType, bool useRamp, Texture2D rampTex, float rampIntensity)
        {
            float softShadowEnabled = shadowType == PerObjectShadowFeature.ShadowType.Soft ? 1.0f : 0.0f;
            Vector4 shadowParams = new Vector4(1.0f, rampIntensity, softShadowEnabled, 0.0f);
            cmd.SetGlobalVector(s_ShadowParamsID, shadowParams);

            if (useRamp && rampTex != null)
            {
                cmd.SetGlobalFloat(s_UseShadowRampID, 1.0f);
                cmd.SetGlobalTexture(s_ShadowRampTexID, rampTex);
            }
            else
            {
                cmd.SetGlobalFloat(s_UseShadowRampID, 0.0f);
                // 给一个默认的白色贴图防止采样出错
                cmd.SetGlobalTexture(s_ShadowRampTexID, Texture2D.whiteTexture);
            }
        }
        
        /// <summary>
        /// 清理资源
        /// </summary>
        public void Dispose()
        {
            m_ScreenSpaceShadowMapTexture?.Release();
            m_ScreenSpaceShadowMapTexture = null;
            m_ResolvedScreenSpaceShadowMapTexture?.Release();
            m_ResolvedScreenSpaceShadowMapTexture = null;

            if (m_ShadowMaterial != null)
            {
                CoreUtils.Destroy(m_ShadowMaterial);
                m_ShadowMaterial = null;
            }

            foreach (var kv in m_SelfStencilMaterials)
            {
                if (kv.Value != null)
                    CoreUtils.Destroy(kv.Value);
            }
            m_SelfStencilMaterials.Clear();
        }
    }
}
