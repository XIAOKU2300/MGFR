using System.Collections.Generic;

namespace UnityEngine.Rendering.Universal
{
    /// <summary>
    /// 第一阶段：阴影图渲染 Pass
    /// 负责为场景中的投射物计算正交相机矩阵并绘制 ShadowMap Atlas
    /// </summary>
    public class PerObjectShadowPass : ScriptableRenderPass
    {
        private static readonly ProfilingSampler s_ProfilingSampler = new ProfilingSampler("PerObjectShadow");

        private PerObjectShadowFeature m_Feature;       // 引用 Feature 获取配置
        private Light m_DirectionalLight;               // 主光源（环境投射参考）
        private Camera m_MainCamera;                    // 主相机（自阴影参考）
        private bool m_EnableVirtualLight;              // 是否开启虚拟光源渲染
        private Quaternion m_VirtualLightRotation;      // 虚拟光源的方向
        private List<PerObjectShadowData> m_ShadowDataList = new List<PerObjectShadowData>(); // 当前帧经过剔除的有效投射物列表
        private List<PerObjectShadowData> m_ShadowDataPool = new List<PerObjectShadowData>(); // 所有帧阴影数据对象池，用于复用数据对象以减少每帧的 GC 内存分配开销
        
        private int m_ValidObjectCount;                // 经过剔除后的有效阴影对象数量
        private Vector2Int m_EnvironmentShadowMapResolution; // 环境阴影图集 (Atlas) 的总分辨率
        private int m_EnvironmentTileResolution;        // 环境阴影图集中单个 Tile 的分辨率
        private Vector2Int m_SelfShadowMapResolution;    // 自阴影图集 (Atlas) 的总分辨率
        private int m_SelfTileResolution;               // 自阴影图集中单个 Tile 的分辨率
        
        private RTHandle m_ShadowMapTexture;            // 环境阴影图
        private RTHandle m_VirtualShadowMapTexture;     // 自阴影图 (虚拟光源)

        // 定义公开变量并传递数据，用于其他 Pass 访问
        public int validObjectCount => m_ValidObjectCount;
        public Vector2Int environmentShadowMapResolution => m_EnvironmentShadowMapResolution;
        public int environmentTileResolution => m_EnvironmentTileResolution;
        public Vector2Int selfShadowMapResolution => m_SelfShadowMapResolution;
        public int selfTileResolution => m_SelfTileResolution;
        public RTHandle shadowMapTexture => m_ShadowMapTexture;
        public RTHandle virtualShadowMapTexture => m_VirtualShadowMapTexture;
        public List<PerObjectShadowData> shadowDataList => m_ShadowDataList;

        // 构造函数，获取Feature数据并初始化
        public PerObjectShadowPass(PerObjectShadowFeature feature)
        {
            m_Feature = feature;
        }

        /// <summary>
        /// 准备渲染数据：执行视锥/距离剔除，计算 Atlas 布局
        /// </summary>
        public bool Setup(Light directionalLight, Camera camera, bool enableVirtualLight, Quaternion virtualLightRotation)
        {
            if (directionalLight == null) return false;

            m_DirectionalLight = directionalLight;
            m_MainCamera = camera;
            m_EnableVirtualLight = enableVirtualLight;
            m_VirtualLightRotation = virtualLightRotation;
            m_ValidObjectCount = 0;
            m_ShadowDataList.Clear();

            // 计算相机视锥平面，用于后续视锥剔除
            Plane[] frustumPlanes = GeometryUtility.CalculateFrustumPlanes(camera);

            foreach (var projector in PerObjectShadowProjector.activeProjectors)
            {
                // 如果已达到最大阴影对象限制，立即停止后续所有剔除计算
                if (m_ValidObjectCount >= m_Feature.maxShadowObjects) break;

                if (projector == null || !projector.IsValid()) continue;

                Bounds projectorBounds = projector.GetBounds(m_Feature.useColliderBounds);

                // 距离剔除
                float distance = Vector3.Distance(camera.transform.position, projectorBounds.center);
                if (distance > m_Feature.drawDistance) continue;

                // 视锥剔除，检测包围盒是否在视锥内
                if (!GeometryUtility.TestPlanesAABB(frustumPlanes, projectorBounds))
                {
                    // 若物体本身不在视锥内，检查其阴影是否可能投射进视锥
                    if (m_Feature.environmentShadow.enabled)
                    {
                        // 计算剔除球，用平面-球面相交测试判断是否在视锥内
                        PerObjectShadowUtils.ComputeCullingSphere(directionalLight, projectorBounds,
                            m_Feature.environmentShadow.farPlaneScale, out var sphereCenter, out var sphereRadius);
                        if (PerObjectShadowUtils.FrustumSphereCulling(frustumPlanes, sphereCenter, sphereRadius))
                            continue;
                    }
                    else continue;
                }

                // 复用数据对象，减少 GC
                PerObjectShadowData shadowData;
                if (m_ValidObjectCount < m_ShadowDataPool.Count)
                    shadowData = m_ShadowDataPool[m_ValidObjectCount];
                else
                {
                    shadowData = new PerObjectShadowData();
                    m_ShadowDataPool.Add(shadowData);
                }

                shadowData.projector = projector;
                shadowData.isCulled = false;
                m_ShadowDataList.Add(shadowData);
                m_ValidObjectCount++;
            }

            if (m_ValidObjectCount == 0) return false;

            // 计算 Atlas 分辨率与 Tile 分配
            m_EnvironmentShadowMapResolution = PerObjectShadowUtils.GetPerObjectShadowMapResolution((int)m_Feature.environmentShadow.shadowMapResolution, m_ValidObjectCount);
            m_EnvironmentTileResolution = PerObjectShadowUtils.GetPerObjectTileResolutionInAtlas(m_EnvironmentShadowMapResolution.x, m_EnvironmentShadowMapResolution.y, m_ValidObjectCount);

            m_SelfShadowMapResolution = PerObjectShadowUtils.GetPerObjectShadowMapResolution((int)m_Feature.selfShadow.shadowMapResolution, m_ValidObjectCount);
            m_SelfTileResolution = PerObjectShadowUtils.GetPerObjectTileResolutionInAtlas(m_SelfShadowMapResolution.x, m_SelfShadowMapResolution.y, m_ValidObjectCount);

            AllocateShadowMapTexture(m_EnvironmentShadowMapResolution, m_SelfShadowMapResolution);
            return true;
        }

        /// <summary>
        /// 分配ShadowMap纹理给RTHandle（分辨率变化时重新分配）
        /// </summary>
        private void AllocateShadowMapTexture(Vector2Int environmentResolution, Vector2Int selfResolution)
        {
            var descriptor = new RenderTextureDescriptor(environmentResolution.x, environmentResolution.y, RenderTextureFormat.Shadowmap, 16);
            descriptor.dimension = TextureDimension.Tex2D;

            if (RenderingUtils.ReAllocateIfNeeded(ref m_ShadowMapTexture, descriptor, FilterMode.Bilinear, TextureWrapMode.Clamp, name: "_PerObjectShadowmapTexture"))
            {
                // Reallocated
            }

            if (m_EnableVirtualLight)
            {
                var virtualDescriptor = new RenderTextureDescriptor(selfResolution.x, selfResolution.y, RenderTextureFormat.Shadowmap, 16);
                virtualDescriptor.dimension = TextureDimension.Tex2D;
                if (RenderingUtils.ReAllocateIfNeeded(ref m_VirtualShadowMapTexture, virtualDescriptor, FilterMode.Bilinear, TextureWrapMode.Clamp, name: "_PerObjectVirtualShadowmapTexture"))
                {
                    // Reallocated
                }
            }
            else
            {
                m_VirtualShadowMapTexture?.Release();
                m_VirtualShadowMapTexture = null;
            }
        }

        /// <summary>
        /// 配置渲染目标和清屏
        /// </summary>
        public override void Configure(CommandBuffer cmd, RenderTextureDescriptor cameraTextureDescriptor)
        {
            if (m_ShadowMapTexture != null)
            {
                ConfigureTarget(m_ShadowMapTexture);
                ConfigureClear(ClearFlag.All, Color.black);
            }
        }

        /// <summary>
        /// 执行渲染 - 遍历有效对象，计算阴影矩阵并渲染ShadowMap
        /// </summary>
        public override void Execute(ScriptableRenderContext context, ref RenderingData renderingData)
        {
            if (m_ValidObjectCount == 0 || m_DirectionalLight == null || m_ShadowMapTexture == null)
                return;

            CommandBuffer cmd = CommandBufferPool.Get("PerObjectShadow");

            using (new ProfilingScope(cmd, new ProfilingSampler("RenderShadows")))//性能分析
            {
                // --- 渲染主光源阴影（环境投射） ---
                cmd.SetRenderTarget(m_ShadowMapTexture);
                cmd.ClearRenderTarget(true, true, Color.black);

                int tileIndex = 0;
                foreach (var shadowData in m_ShadowDataList)
                {
                    if (shadowData.isCulled || shadowData.projector == null)
                        continue;

                    var projector = shadowData.projector;
                    Bounds projectorBounds = projector.GetBounds(m_Feature.useColliderBounds);

                    //计算完整的阴影切片数据（矩阵+Atlas偏移+UV变换）
                    PerObjectShadowUtils.ExtractDirectionalLightMatrix(
                        tileIndex, m_DirectionalLight, projectorBounds, m_Feature.environmentShadow.farPlaneScale,
                        m_EnvironmentShadowMapResolution.x, m_EnvironmentShadowMapResolution.y, m_EnvironmentTileResolution,
                        out var sliceData);

                    shadowData.mainSliceData = sliceData;

                    if (m_Feature.environmentShadow.enabled)
                    {//计算阴影偏移参数
                        Vector4 shadowBias = PerObjectShadowUtils.GetShadowBias(
                            m_DirectionalLight, m_Feature.environmentShadow.depthBias, m_Feature.environmentShadow.normalBias,
                            sliceData.projectionMatrix, m_EnvironmentTileResolution);
                        
                        //设置ShadowCaster Pass所需的Shader全局变量
                        PerObjectShadowUtils.SetupShadowCasterConstantBuffer(cmd, m_DirectionalLight, shadowBias);

                        Material shadowMaterial = projector.shadowMaterial;
                        if (shadowMaterial == null)
                        {
                            Debug.LogWarning($"PerObjectShadow: {projector.name} 没有阴影材质，跳过渲染");
                            continue;
                        }

                        shadowMaterial.enableInstancing = true;
                        int passIndex = shadowMaterial.FindPass("ShadowCaster");
                        var renderersToDraw = projector.childRenderers;

                        //硬件级的多边形偏移，解决阴影 acne 问题
                        cmd.SetGlobalDepthBias(1.0f, 2.5f);
                        PerObjectShadowUtils.RenderShadowSlice(cmd, renderersToDraw, ref sliceData, shadowMaterial, passIndex);
                        cmd.SetGlobalDepthBias(0.0f, 0.0f);
                    }

                    tileIndex++;
                }

                // --- 渲染虚拟光源阴影 ---
                if (m_EnableVirtualLight && m_VirtualShadowMapTexture != null)
                {
                    cmd.SetRenderTarget(m_VirtualShadowMapTexture);
                    cmd.ClearRenderTarget(true, true, Color.black);

                    tileIndex = 0;
                    foreach (var shadowData in m_ShadowDataList)
                    {
                        if (shadowData.isCulled || shadowData.projector == null) continue;

                        var projector = shadowData.projector;
                        Bounds projectorBounds = projector.GetBounds(m_Feature.useColliderBounds);
                        Vector3 virtualLightPos = projectorBounds.center; // 正交投影只看方向，位置放中心即可

                        PerObjectShadowSliceData sliceData;
                        if (m_Feature.selfShadow.followCamera)
                        {
                            PerObjectShadowUtils.ExtractSelfShadowMatrix(
                                tileIndex, m_VirtualLightRotation, virtualLightPos, projectorBounds, m_MainCamera, m_Feature.selfShadow.farPlaneScale,
                                m_SelfShadowMapResolution.x, m_SelfShadowMapResolution.y, m_SelfTileResolution, m_Feature.selfShadow.followCameraOrthoSizeScale,
                                out sliceData);
                            shadowData.virtualSliceData = sliceData;
                        }
                        else
                        {
                            PerObjectShadowUtils.ExtractDirectionalLightMatrix(
                                tileIndex, m_VirtualLightRotation, virtualLightPos, projectorBounds, m_Feature.selfShadow.farPlaneScale,
                                m_SelfShadowMapResolution.x, m_SelfShadowMapResolution.y, m_SelfTileResolution,
                                out sliceData);
                            shadowData.virtualSliceData = sliceData;
                        }

                        Vector4 shadowBias = PerObjectShadowUtils.GetShadowBias(
                            m_DirectionalLight, m_Feature.selfShadow.depthBias, m_Feature.selfShadow.normalBias, sliceData.projectionMatrix, m_SelfTileResolution);
                        PerObjectShadowUtils.SetupShadowCasterConstantBuffer(cmd, m_VirtualLightRotation, virtualLightPos, shadowBias);

                        Material shadowMaterial = projector.shadowMaterial;
                        if (shadowMaterial == null) continue;
                        shadowMaterial.enableInstancing = true;
                        int passIndex = shadowMaterial.FindPass("ShadowCaster");

                        cmd.SetGlobalDepthBias(1.0f, 2.5f);
                        PerObjectShadowUtils.RenderShadowSlice(cmd, projector.childRenderers, ref sliceData, shadowMaterial, passIndex);
                        cmd.SetGlobalDepthBias(0.0f, 0.0f);

                        tileIndex++;
                    }
                }
            }

            context.ExecuteCommandBuffer(cmd);
            CommandBufferPool.Release(cmd);
        }

        /// <summary>
        /// 释放ShadowMap纹理资源
        /// </summary>
        public void Dispose()
        {
            m_ShadowMapTexture?.Release();
            m_ShadowMapTexture = null;
            m_VirtualShadowMapTexture?.Release();
            m_VirtualShadowMapTexture = null;
        }
    }
}
