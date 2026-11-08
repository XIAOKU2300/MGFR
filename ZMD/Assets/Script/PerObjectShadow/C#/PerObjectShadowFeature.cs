using UnityEngine;
using UnityEngine.Rendering;

namespace UnityEngine.Rendering.Universal
{
    /// <summary>
    /// PerObjectShadow 渲染特性
    /// 入口类，负责创建 Pass 并在合适时机入队
    /// </summary>
    [DisallowMultipleRendererFeature("Per Object Shadow")]
    [Tooltip("Per Object Shadow - 为每个对象渲染独立的阴影")]
    public class PerObjectShadowFeature : ScriptableRendererFeature
    {
        /// <summary>
        /// 环境阴影配置
        /// </summary>
        [System.Serializable]
        public class EnvironmentShadowSettings
        {
            [Tooltip("是否启用环境投射")] public bool enabled = true;
            [Tooltip("ShadowMap 分辨率")] public ShadowMapResolution shadowMapResolution = ShadowMapResolution.Resolution2048;
            [Tooltip("阴影类型")] public ShadowType shadowType = ShadowType.Soft;
            [Tooltip("开启 Shadow Ramp")] public bool useRamp = false;
            [Tooltip("Ramp 混合强度")] [Range(0f, 1f)] public float rampIntensity = 1.0f;
            [Tooltip("实时渐变色调节")] public Gradient shadowGradient = new Gradient();
            
            [HideInInspector] public Texture2D bakedRampTex; // 动态烘焙的渐变贴图
            private Color[] m_CachedPixels;                  // 像素缓存，优化提交性能
            private bool m_IsDirty = true;

            /// <summary>
            /// 将 Gradient 烘焙到纹理，仅在变化时更新 GPU
            /// </summary>
            public void BakeGradient()
            {
                BakeGradientInternal(ref bakedRampTex, ref m_CachedPixels, ref m_IsDirty, shadowGradient);
            }

            public void Cleanup()
            {
                CleanupGradientInternal(ref bakedRampTex, ref m_CachedPixels, ref m_IsDirty);
            }
            [Tooltip("PCF 采样质量")] public PCFQuality pcfQuality = PCFQuality.Medium_5x5;
            [Tooltip("深度偏移")] [Range(0f, 10f)] public float depthBias = 1.0f;
            [Tooltip("法线偏移")] [Range(0f, 10f)] public float normalBias = 1.0f;
            [Tooltip("阴影相机远平面缩放")] [Range(0f, 5f)] public float farPlaneScale = 5.0f;
        }

        /// <summary>
        /// 角色自阴影配置 (虚拟光源)
        /// </summary>
        [System.Serializable]
        public class SelfShadowSettings
        {
            [Tooltip("是否启用自阴影")] public bool enabled = true;
            [Tooltip("ShadowMap 分辨率")] public ShadowMapResolution shadowMapResolution = ShadowMapResolution.Resolution1024;
            [Tooltip("阴影类型")] public ShadowType shadowType = ShadowType.Soft;
            [Tooltip("开启 Shadow Ramp")] public bool useRamp = false;
            [Tooltip("Ramp 混合强度")] [Range(0f, 1f)] public float rampIntensity = 1.0f;
            [Tooltip("实时渐变色调节")] public Gradient shadowGradient = new Gradient();

            [HideInInspector] public Texture2D bakedRampTex;
            private Color[] m_CachedPixels;
            private bool m_IsDirty = true;

            public void BakeGradient()
            {
                BakeGradientInternal(ref bakedRampTex, ref m_CachedPixels, ref m_IsDirty, shadowGradient);
            }

            public void Cleanup()
            {
                CleanupGradientInternal(ref bakedRampTex, ref m_CachedPixels, ref m_IsDirty);
            }

            [Tooltip("PCF 采样质量")] public PCFQuality pcfQuality = PCFQuality.Medium_5x5;
            [Tooltip("深度偏移")] [Range(0f, 10f)] public float depthBias = 1.0f;
            [Tooltip("法线偏移")] [Range(0f, 10f)] public float normalBias = 1.0f;
            
            [Header("相机跟随限制")]
            [Tooltip("X轴旋转最小值")] [Range(-90f, 90f)] public float minPitch = 30f;
            [Tooltip("X轴旋转最大值")] [Range(-90f, 90f)] public float maxPitch = 35f;
            
            [Tooltip("阴影相机远平面缩放")] [Range(0f, 5f)] public float farPlaneScale = 0.5f;
            [Tooltip("相机跟随 (提高近景精度)")] public bool followCamera = true;
            [Tooltip("跟随相机 OrthoSize 缩放 (\u003e1 放大覆盖，\u003c1 提高精度)")] [Range(0.1f, 3f)] public float followCameraOrthoSizeScale = 1.0f;
        }

        public enum ShadowCasterPassTiming
        {
            BeforeRenderingShadows = 0,     // URP 主阴影渲染前 (默认)
            AfterRenderingShadows = 1,      // URP 主阴影渲染后
            BeforeRenderingPrePasses = 2,   // 深度/法线预转前
        }

        public enum ScreenSpacePassTiming
        {
            AfterPrePasses = 0,             // 深度预转后
            AfterOpaques = 1,               // 不透明物体渲染后 (默认)
            AfterSkybox = 2,                // 天空盒渲染后
            BeforeRenderingTransparents = 3, // 半透明物体渲染前 (推荐：可规避 SSAO 冲突)
            BeforePostProcessing = 4,       // 后处理渲染前
            AfterRendering = 5,             // 全部渲染完成后
        }

        public enum ShadowMapResolution
        {
            Resolution512 = 512,
            Resolution1024 = 1024,
            Resolution2048 = 2048,
            Resolution4096 = 4096,
        }

        public enum PCFQuality
        {
            Low_3x3 = 0,
            Medium_5x5 = 1,
            High_7x7 = 2,
        }

        public enum ShadowType
        {
            Hard = 0,
            Soft = 1,
        }

        private const int k_GradientTexWidth = 256;
        //生成渐变纹理
        private static void BakeGradientInternal(ref Texture2D bakedRampTex, ref Color[] cachedPixels, ref bool isDirty, Gradient gradient)
        {
            if (bakedRampTex == null)
            {//定义texture2d属性
                bakedRampTex = new Texture2D(k_GradientTexWidth, 1, TextureFormat.ARGB32, false, true);
                bakedRampTex.wrapMode = TextureWrapMode.Clamp;
                bakedRampTex.filterMode = FilterMode.Bilinear;
                bakedRampTex.hideFlags = HideFlags.HideAndDontSave;
                isDirty = true;
            }

            if (cachedPixels == null || cachedPixels.Length != k_GradientTexWidth)
            {
                cachedPixels = new Color[k_GradientTexWidth];
                isDirty = true;
            }

            bool changed = false;
            for (int i = 0; i < k_GradientTexWidth; i++)
            {
                Color col = gradient.Evaluate((float)i / (k_GradientTexWidth - 1));
                if (cachedPixels[i] != col)
                {
                    cachedPixels[i] = col;
                    changed = true;//用极小的 CPU 开销换取极大的 GPU 性能提升，apply()更耗
                }
            }

            if (changed || isDirty)
            {
                bakedRampTex.SetPixels(cachedPixels);// 将像素数据从 CPU 数组拷贝到纹理
                bakedRampTex.Apply(false, false);    // 真正将纹理上传到 GPU 显存
                isDirty = false;
            }
        }
        //清理渐变纹理
        private static void CleanupGradientInternal(ref Texture2D bakedRampTex, ref Color[] cachedPixels, ref bool isDirty)
        {
            if (bakedRampTex != null)
            {
                CoreUtils.Destroy(bakedRampTex);
                bakedRampTex = null;
            }

            cachedPixels = null;
            isDirty = true;
        }

        #region 配置参数

        [Header("通用设置")]
        [Tooltip("最大阴影对象数量")][Range(1, 32)] public int maxShadowObjects = 16;
        [Tooltip("阴影绘制距离")] public float drawDistance = 100f;
        [Tooltip("是否优先使用碰撞体包围盒计算阴影")] public bool useColliderBounds = true;
        [Tooltip("ShadowMap 渲染 Pass 的执行时机")] public ShadowCasterPassTiming shadowCasterPassTiming = ShadowCasterPassTiming.BeforeRenderingShadows;
        [Tooltip("屏幕空间阴影 Pass 的执行时机")] public ScreenSpacePassTiming screenSpacePassTiming = ScreenSpacePassTiming.AfterOpaques;

        [Header("环境投射设置")]
        public EnvironmentShadowSettings environmentShadow = new EnvironmentShadowSettings();

        [Header("自阴影设置")]
        public SelfShadowSettings selfShadow = new SelfShadowSettings();

        #endregion

        private PerObjectShadowPass m_ShadowCasterPass;       // ShadowMap 渲染 Pass
        private PerObjectTransparentDepthPass m_TransparentDepthPass; // 半透明深度预写入 Pass
        private PerObjectScreenSpaceShadowsPass m_ScreenSpaceShadowsPass;  // 屏幕空间阴影 Pass
        private Light m_MainLight;

        /// <summary>
        /// 创建 Pass，设置在阴影渲染前执行
        /// </summary>
        public override void Create()
        {
            m_ShadowCasterPass?.Dispose();
            m_ShadowCasterPass = null;

            m_ScreenSpaceShadowsPass?.Dispose();
            m_ScreenSpaceShadowsPass = null;

            m_TransparentDepthPass?.Dispose();
            m_TransparentDepthPass = null;

            // 初始烘焙一次
            environmentShadow.BakeGradient();
            selfShadow.BakeGradient();

            // ShadowMap Caster Pass - 在阴影渲染前执行
            m_ShadowCasterPass = new PerObjectShadowPass(this)
            {
                renderPassEvent = RenderPassEvent.BeforeRenderingShadows
            };

            m_TransparentDepthPass = new PerObjectTransparentDepthPass
            {
                renderPassEvent = (RenderPassEvent)((int)RenderPassEvent.AfterRenderingOpaques + 1)
            };

            // Screen Space Shadow Pass
            m_ScreenSpaceShadowsPass = new PerObjectScreenSpaceShadowsPass(this)
            {
                renderPassEvent = (RenderPassEvent)((int)RenderPassEvent.AfterRenderingOpaques + 1)
            };
        }

        /// <summary>
        /// 每帧调用，判断是否需要渲染并入队
        /// </summary>
        public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
        {
            // 排除预览相机，提升编辑器性能和稳定性
            if (renderingData.cameraData.cameraType == CameraType.Preview)
                return;

            // 每帧烘焙一次以确保实时更新
            environmentShadow.BakeGradient();
            selfShadow.BakeGradient();

            // 判定入队条件
            // 检查主光源是否存在，分索引层和对象层两步
            int mainLightIndex = renderingData.lightData.mainLightIndex;
            if (mainLightIndex == -1)
                return;

            var visibleLight = renderingData.lightData.visibleLights[mainLightIndex];
            m_MainLight = visibleLight.light;

            if (m_MainLight == null)
                return;

            // 只支持方向光
            if (visibleLight.lightType != LightType.Directional)
            {
                Debug.LogWarning("PerObjectShadow: 只支持方向光");
                return;
            }

            // 检查是否有激活的阴影投射者
            if (PerObjectShadowProjector.activeProjectors.Count == 0)
                return;

            // 获取主光源旋转和位置
            Quaternion mainLightRotation = m_MainLight.transform.rotation;
            Vector3 mainLightPosition = m_MainLight.transform.position;

            // 定义虚拟光源旋转 (随主相机变化)
            Quaternion virtualLightRotation = Quaternion.identity;
            if (selfShadow.enabled)
            {
                // xyz 都与主摄像机同步，并限制 x 轴旋转
                Vector3 cameraEuler = renderingData.cameraData.camera.transform.eulerAngles;
                
                // 处理欧拉角，使其在 -180 到 180 范围内，方便限制
                float pitch = cameraEuler.x;
                if (pitch > 180f) pitch -= 360f;
                
                // 限制 x 轴
                pitch = Mathf.Clamp(pitch, selfShadow.minPitch, selfShadow.maxPitch);
                
                virtualLightRotation = Quaternion.Euler(pitch, cameraEuler.y, cameraEuler.z);
            }

            // 确定ShadowCasterPass渲染时机
            if (m_ShadowCasterPass != null)
            {
                switch (shadowCasterPassTiming)
                {
                    case ShadowCasterPassTiming.BeforeRenderingShadows:
                        m_ShadowCasterPass.renderPassEvent = RenderPassEvent.BeforeRenderingShadows;
                        break;
                    case ShadowCasterPassTiming.AfterRenderingShadows:
                        m_ShadowCasterPass.renderPassEvent = RenderPassEvent.AfterRenderingShadows;
                        break;
                    case ShadowCasterPassTiming.BeforeRenderingPrePasses:
                        m_ShadowCasterPass.renderPassEvent = RenderPassEvent.BeforeRenderingPrePasses;
                        break;
                }
            }

            // 确定ScreenSpaceShadowsPass渲染时机
            if (m_ScreenSpaceShadowsPass != null)
            {
                switch (screenSpacePassTiming)
                {
                    case ScreenSpacePassTiming.AfterPrePasses:
                        m_ScreenSpaceShadowsPass.renderPassEvent = RenderPassEvent.AfterRenderingPrePasses;
                        break;
                    case ScreenSpacePassTiming.AfterOpaques:
                        m_ScreenSpaceShadowsPass.renderPassEvent = (RenderPassEvent)((int)RenderPassEvent.AfterRenderingOpaques + 1);
                        break;
                    case ScreenSpacePassTiming.AfterSkybox:
                        m_ScreenSpaceShadowsPass.renderPassEvent = RenderPassEvent.AfterRenderingSkybox;
                        break;
                    case ScreenSpacePassTiming.BeforeRenderingTransparents:
                        m_ScreenSpaceShadowsPass.renderPassEvent = RenderPassEvent.BeforeRenderingTransparents;
                        break;
                    case ScreenSpacePassTiming.BeforePostProcessing:
                        m_ScreenSpaceShadowsPass.renderPassEvent = RenderPassEvent.BeforeRenderingPostProcessing;
                        break;
                    case ScreenSpacePassTiming.AfterRendering:
                        m_ScreenSpaceShadowsPass.renderPassEvent = RenderPassEvent.AfterRendering;
                        break;
                }

                if (m_TransparentDepthPass != null)
                    m_TransparentDepthPass.renderPassEvent = m_ScreenSpaceShadowsPass.renderPassEvent;
            }

            // Setup 成功则入队
            if (m_ShadowCasterPass.Setup(m_MainLight, renderingData.cameraData.camera, selfShadow.enabled, virtualLightRotation))
            {
                renderer.EnqueuePass(m_ShadowCasterPass);
            }

            if (m_ScreenSpaceShadowsPass.Setup(
                m_ShadowCasterPass.shadowMapTexture,
                m_ShadowCasterPass.virtualShadowMapTexture,
                m_ShadowCasterPass.shadowDataList,
                m_ShadowCasterPass.validObjectCount,
                m_ShadowCasterPass.environmentShadowMapResolution,
                m_ShadowCasterPass.environmentTileResolution,
                m_ShadowCasterPass.selfShadowMapResolution,
                m_ShadowCasterPass.selfTileResolution,
                selfShadow.enabled))
            {
                if (m_TransparentDepthPass != null)
                    renderer.EnqueuePass(m_TransparentDepthPass);
                renderer.EnqueuePass(m_ScreenSpaceShadowsPass);
            }
        }

        // 资源清理
        protected override void Dispose(bool disposing)
        {
            // 清理渐变纹理
            environmentShadow.Cleanup();
            selfShadow.Cleanup();

            m_ShadowCasterPass?.Dispose();
            m_ShadowCasterPass = null;

            m_TransparentDepthPass?.Dispose();
            m_TransparentDepthPass = null;
            
            m_ScreenSpaceShadowsPass?.Dispose();
            m_ScreenSpaceShadowsPass = null;
        }
    }
}
