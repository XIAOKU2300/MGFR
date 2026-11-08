using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using MGFR.Dialogue;

namespace MGFR.Repairs
{
    /// <summary>Preserve transcript text/atlas/visibility; only repair RGB-key compositing.</summary>
    [DefaultExecutionOrder(32100)]
    public sealed class SubtitleChromaRepair : MonoBehaviour
    {
        readonly List<Material> materials = new List<Material>();
        readonly List<Shader> previousShaders = new List<Shader>();
        Shader replacement;
        float nextFind;
        public bool Ready => replacement != null && materials.Count == 2;
        public int MaterialCount => materials.Count;

        // Integration calls once after loading the shared repair shader asset bundle.
        public void Initialize(Shader shader)
        {
            if (shader == null || !shader.isSupported) throw new ArgumentException("A supported ChatOverlayChroma shader is required");
            replacement = shader;
            Bind();
        }
        void OnEnable() { Camera.onPreRender += BeforeCamera; }
        void OnDisable() { Camera.onPreRender -= BeforeCamera; Restore(); }
        void LateUpdate()
        {
            if(replacement != null && Time.unscaledTime >= nextFind)
            { nextFind = Time.unscaledTime + 1f; Bind(); }
        }
        void Bind()
        {
            foreach(var overlay in FindObjectsByType<CameraChatOverlay>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            foreach(var renderer in overlay.GetComponentsInChildren<MeshRenderer>(true))
            {
                Material material = renderer.sharedMaterial;
                if(material == null || materials.Contains(material)) continue;
                // The live overlay retains this Material and refreshes its font atlas on Rebuild.
                // Cloning here would break that atlas update contract.
                if(material.shader == null || (material.shader.name != "MGFR/ChatOverlay" && material.shader != replacement)) continue;
                materials.Add(material); previousShaders.Add(material.shader);
                int queue = material.renderQueue; material.shader = replacement; material.renderQueue = queue;
            }
        }
        public static bool IsKeyCamera(Camera camera)
        {
            if(camera == null || camera.clearFlags != CameraClearFlags.SolidColor) return false;
            Color c = camera.backgroundColor;
            return c.r < .001f && c.g > .999f && c.b < .001f;
        }
        public void ConfigureForCamera(Camera camera)
        {
            bool keyed = IsKeyCamera(camera);
            foreach(var material in materials)
            {
                if(material == null) continue;
                material.SetFloat("_KeyCoverage", keyed ? 1f : 0f);
                material.SetFloat("_SrcBlend", keyed ? (float)BlendMode.One : (float)BlendMode.SrcAlpha);
                material.SetFloat("_DstBlend", keyed ? (float)BlendMode.Zero : (float)BlendMode.OneMinusSrcAlpha);
            }
            // Spatial coverage must reach the RGB-key transport without MSAA mixing it back into green.
            if(keyed) camera.allowMSAA = false;
        }
        void BeforeCamera(Camera camera) { ConfigureForCamera(camera); }
        void Restore()
        {
            for(int i=0;i<materials.Count;i++)
                if(materials[i] != null && materials[i].shader == replacement) materials[i].shader=previousShaders[i];
            materials.Clear(); previousShaders.Clear();
        }
    }
}
