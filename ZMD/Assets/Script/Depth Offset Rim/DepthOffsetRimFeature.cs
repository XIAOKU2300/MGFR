using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

public class DepthOffsetRimFeature : ScriptableRendererFeature
{
    [System.Serializable]
    public class Settings
    {
        public RenderPassEvent renderPassEvent = RenderPassEvent.BeforeRenderingPostProcessing;
        public Shader shader;
        
        [Header("Rim Settings")]
        [Range(0, 0.1f)] public float offsetMul = 0.012f;
        [Range(0, 1f)] public float threshold = 0.09f;
        [Range(0, 1f)] public float smooth = 0.05f;
        public Color rimColor = Color.white;
        public float rimIntensity = 1.0f;
        
        [Header("Layer Mask")]
        [Tooltip("只有属于此 LayerMask 的物体才会产生边缘光")]
        public LayerMask characterLayerMask = -1;
    }

    public Settings settings = new Settings();
    private DepthOffsetRimPass pass;

    public override void Create()
    {
        if (settings.shader == null) return;
        
        // 防止 Inspector 刷新时频繁实例化导致 RTHandle 泄漏
        if (pass == null)
        {
            pass = new DepthOffsetRimPass(settings);
        }
        else
        {
            pass.UpdateSettings(settings);
        }
    }

    protected override void Dispose(bool disposing)
    {
        pass?.Dispose();
    }

    public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
    {
        if (settings.shader == null) return;
        // 仅在游戏视图和场景视图生效
        if (renderingData.cameraData.cameraType != CameraType.Game && renderingData.cameraData.cameraType != CameraType.SceneView) return;

        renderer.EnqueuePass(pass);
    }

    class DepthOffsetRimPass : ScriptableRenderPass
    {
        private Settings settings;
        private Material material;
        private Material maskMaterial;
        private RTHandle source;
        private RTHandle charMaskHandle;
        private RTHandle charMaskResolvedHandle;
        private FilteringSettings filteringSettings;
        private ProfilingSampler profilingSampler = new ProfilingSampler("DepthOffsetRim_CharacterMask");

        public DepthOffsetRimPass(Settings settings)
        {
            UpdateSettings(settings);

            if (maskMaterial == null)
            {
                Shader unlitShader = Shader.Find("Universal Render Pipeline/Unlit");
                if (unlitShader != null)
                {
                    maskMaterial = CoreUtils.CreateEngineMaterial(unlitShader);
                    maskMaterial.SetColor("_BaseColor", Color.white);
                }
            }
        }

        public void UpdateSettings(Settings newSettings)
        {
            this.settings = newSettings;
            this.renderPassEvent = newSettings.renderPassEvent;
            this.filteringSettings = new FilteringSettings(RenderQueueRange.opaque, newSettings.characterLayerMask);

            if (material != null && material.shader != newSettings.shader)
            {
                CoreUtils.Destroy(material);
                material = null;
            }
            if (material == null && newSettings.shader != null)
            {
                material = CoreUtils.CreateEngineMaterial(newSettings.shader);
            }
        }

        public override void OnCameraSetup(CommandBuffer cmd, ref RenderingData renderingData)
        {
            source = renderingData.cameraData.renderer.cameraColorTargetHandle;
            ConfigureInput(ScriptableRenderPassInput.Depth);

            RenderTextureDescriptor opaqueDesc = renderingData.cameraData.cameraTargetDescriptor;
            opaqueDesc.depthBufferBits = 0;
            
            RenderTextureDescriptor resolveDesc = opaqueDesc;
            resolveDesc.msaaSamples = 1;

            RenderingUtils.ReAllocateIfNeeded(ref charMaskHandle, opaqueDesc, FilterMode.Point, TextureWrapMode.Clamp, name: "_CharacterMaskTextureMSAA");
            RenderingUtils.ReAllocateIfNeeded(ref charMaskResolvedHandle, resolveDesc, FilterMode.Point, TextureWrapMode.Clamp, name: "_CharacterMaskTexture");
        }

        public override void Execute(ScriptableRenderContext context, ref RenderingData renderingData)
        {
            if (material == null) return;

            CommandBuffer cmd = CommandBufferPool.Get("DepthOffsetRim_PP");

            // 传递参数到 Shader
            material.SetFloat("_OffsetMul", settings.offsetMul);
            material.SetFloat("_Threshold", settings.threshold);
            material.SetFloat("_Smooth", settings.smooth);
            material.SetColor("_RimLightColor", settings.rimColor);
            material.SetFloat("_RimIntensity", settings.rimIntensity);

            cmd.SetRenderTarget(charMaskHandle, renderingData.cameraData.renderer.cameraDepthTargetHandle);
            cmd.ClearRenderTarget(false, true, Color.clear);
            context.ExecuteCommandBuffer(cmd);
            cmd.Clear();

            if (maskMaterial != null)
            {
                DrawingSettings drawingSettings = CreateDrawingSettings(new ShaderTagId("UniversalForward"), ref renderingData, SortingCriteria.CommonOpaque);
                drawingSettings.SetShaderPassName(1, new ShaderTagId("LightweightForward"));
                drawingSettings.SetShaderPassName(2, new ShaderTagId("SRPDefaultUnlit"));
                drawingSettings.overrideMaterial = maskMaterial;
                drawingSettings.overrideMaterialPassIndex = 0;

                using (new ProfilingScope(cmd, profilingSampler))
                {
                    context.DrawRenderers(renderingData.cullResults, ref drawingSettings, ref filteringSettings);
                }
            }

            cmd.Blit(charMaskHandle, charMaskResolvedHandle);

            cmd.SetRenderTarget(source);
            cmd.SetGlobalTexture("_CharacterMaskTexture", charMaskResolvedHandle);
            
            CoreUtils.DrawFullScreen(cmd, material);

            context.ExecuteCommandBuffer(cmd);
            CommandBufferPool.Release(cmd);
        }

        public void Dispose()
        {
            charMaskHandle?.Release();
            charMaskResolvedHandle?.Release();
            if (material != null) CoreUtils.Destroy(material);
            if (maskMaterial != null) CoreUtils.Destroy(maskMaterial);
        }
    }
}