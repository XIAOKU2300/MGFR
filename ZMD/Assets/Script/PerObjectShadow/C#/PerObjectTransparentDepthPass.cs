using UnityEngine;
using UnityEngine.Rendering;

namespace UnityEngine.Rendering.Universal
{
    public class PerObjectTransparentDepthPass : ScriptableRenderPass
    {
        private static readonly ProfilingSampler s_ProfilingSampler = new ProfilingSampler("PerObject Transparent Depth");
        private static readonly int s_TransparentDepthTextureID = Shader.PropertyToID("_PerObjectTransparentDepthTexture");
        private static readonly ShaderTagId s_ShaderTagId = new ShaderTagId("TransparentDepthPrepass");

        private RTHandle m_TransparentDepthTexture;

        public override void OnCameraSetup(CommandBuffer cmd, ref RenderingData renderingData)
        {
            RenderTextureDescriptor descriptor = renderingData.cameraData.cameraTargetDescriptor;
            descriptor.colorFormat = RenderTextureFormat.Depth;
            descriptor.depthBufferBits = 32;
            descriptor.msaaSamples = 1;
            descriptor.bindMS = false;
            descriptor.useMipMap = false;
            descriptor.autoGenerateMips = false;

            RenderingUtils.ReAllocateIfNeeded(ref m_TransparentDepthTexture, descriptor, FilterMode.Point, TextureWrapMode.Clamp, name: "_PerObjectTransparentDepthTexture");

            ConfigureTarget(m_TransparentDepthTexture);
            ConfigureClear(ClearFlag.Depth, Color.black);
        }

        public override void Execute(ScriptableRenderContext context, ref RenderingData renderingData)
        {
            if (m_TransparentDepthTexture == null)
                return;

            CommandBuffer cmd = CommandBufferPool.Get("PerObjectTransparentDepth");

            using (new ProfilingScope(cmd, s_ProfilingSampler))
            {
                DrawingSettings drawingSettings = CreateDrawingSettings(s_ShaderTagId, ref renderingData, SortingCriteria.CommonTransparent);
                FilteringSettings filteringSettings = new FilteringSettings(RenderQueueRange.transparent);

                context.ExecuteCommandBuffer(cmd);
                cmd.Clear();

                context.DrawRenderers(renderingData.cullResults, ref drawingSettings, ref filteringSettings);
                cmd.SetGlobalTexture(s_TransparentDepthTextureID, m_TransparentDepthTexture.nameID);
                cmd.SetRenderTarget(renderingData.cameraData.renderer.cameraDepthTargetHandle.nameID);

                context.ExecuteCommandBuffer(cmd);
                cmd.Clear();

                context.DrawRenderers(renderingData.cullResults, ref drawingSettings, ref filteringSettings);
            }

            context.ExecuteCommandBuffer(cmd);
            CommandBufferPool.Release(cmd);
        }

        public void Dispose()
        {
            m_TransparentDepthTexture?.Release();
            m_TransparentDepthTexture = null;
        }
    }
}