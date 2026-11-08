using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

/// 毛发渲染特性：用于在URP中实现多层毛发效果
/// 通过Shell渲染技术，多次绘制同一网格并逐层偏移来模拟毛发体积感
/// 每个对象使用自己的材质，支持不同对象使用不同材质参数
public class FurFeature : ScriptableRendererFeature
{
    [Header("【渲染时机】")]
    [Space(20)]
    public RenderPassEvent passEvent = RenderPassEvent.AfterRenderingSkybox;

    [Header("【过滤】")]
    [Space(20)]
    public RenderQueueType queue = RenderQueueType.Transparent;
    public enum RenderQueueType
    {
        Opaque,
        Transparent,
    };

    [Header("【渲染参数】")]
    [Space(20)]
    [Range(2, 100)] public int step = 10;

    /// 毛发渲染Pass：继承ScriptableRenderPass，负责实际的渲染执行逻辑
    class FurPass : ScriptableRenderPass
    {
        private int step;
        private FilteringSettings filteringSettings;
        private RenderQueueType renderQueueType;
        private List<ShaderTagId> tagIds;

        /// 构造函数：初始化渲染Pass的各项配置
        public FurPass(int step, RenderPassEvent renderPassEvent, RenderQueueType renderQueueType)
        {
            this.step = step;
            this.renderPassEvent = renderPassEvent;
            this.renderQueueType = renderQueueType;

            // 根据渲染队列类型(透明/不透明)创建过滤设置
            RenderQueueRange renderQueueRange = (renderQueueType == RenderQueueType.Transparent)
                ? RenderQueueRange.transparent
                : RenderQueueRange.opaque;
            filteringSettings = new FilteringSettings(renderQueueRange);

            // 使用 FurShell LightMode Tag 筛选需要渲染的毛发对象
            tagIds = new List<ShaderTagId> { new ShaderTagId("FurShell") };
        }

        /// 核心渲染逻辑：执行多层毛发渲染
        /// 使用Shell渲染技术，循环绘制多层，每层设置不同的毛发高度参数
        public override void Execute(ScriptableRenderContext context, ref RenderingData renderingData)
        {
            // 根据渲染队列类型选择合适的排序策略
            // 透明物体需要从后向前排序，不透明物体使用默认排序
            SortingCriteria sortingCriteria = (renderQueueType == RenderQueueType.Transparent)
                ? SortingCriteria.CommonTransparent
                : renderingData.cameraData.defaultOpaqueSortFlags;

            // 创建绘制设置：不使用overrideMaterial，每个对象使用自己的材质
            DrawingSettings drawingSettings = CreateDrawingSettings(tagIds, ref renderingData, sortingCriteria);

            // 多层渲染：每层设置不同的_Fur_Height01_GLB值(0-1)，实现毛发从根部到顶部的渐变效果
            CommandBuffer cmd = CommandBufferPool.Get("FurRendering");
            // 设置总层数全局变量，供材质的层数限制clip使用
            cmd.SetGlobalFloat("_FurTotalLayers_GLB", step);
            context.ExecuteCommandBuffer(cmd);
            cmd.Clear();

            for (int i = 0; i < step; i++)
            {
                // 计算当前层的高度比例，作为全局参数传递给Shader
                cmd.SetGlobalFloat("_Fur_Height01_GLB", i / (step - 1.0f));
                context.ExecuteCommandBuffer(cmd);
                cmd.Clear();
                // 绘制所有使用 FurShell LightMode 的对象，每个对象使用自己的材质
                context.DrawRenderers(renderingData.cullResults, ref drawingSettings, ref filteringSettings);
            }
            CommandBufferPool.Release(cmd);
        }
    }

    FurPass furPass;

    /// 创建渲染Pass实例，将配置参数传入
    /// 此方法在Feature首次创建或Inspector修改时调用
    public override void Create()
    {
        furPass = new FurPass(step, passEvent, queue);
    }

    /// 将自定义渲染Pass注入到渲染管线队列中
    /// 每帧每相机渲染时都会调用此方法
    public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
    {
        if (furPass != null)
        {
            renderer.EnqueuePass(furPass);
        }
    }
}