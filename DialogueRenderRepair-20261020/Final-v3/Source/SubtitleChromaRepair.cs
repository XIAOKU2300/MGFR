using System;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Dialogue;

namespace MGFR.Repairs
{
    [DefaultExecutionOrder(32100)]
    public sealed class SubtitleChromaRepair : MonoBehaviour
    {
        const string GlobalKey="_MGFRRgbKeyCoverage";
        readonly List<Material> materials=new List<Material>();
        readonly List<Shader> previousShaders=new List<Shader>();
        readonly Stack<float> cameraKeyStack=new Stack<float>();
        readonly Stack<float> cameraDepthStack=new Stack<float>();
        Shader replacement;float nextFind;
        public bool Ready=>replacement!=null && materials.Count==2;
        public int MaterialCount=>materials.Count;

        // Bundle asset: Assets/ChatOverlayChroma.shader. Call once after bundle load.
        public static SubtitleChromaRepair Install(Shader shader)
        {
            var owner=FindAnyObjectByType<SubtitleChromaRepair>();
            if(owner==null)owner=new GameObject("RGB key camera and subtitle composite repair").AddComponent<SubtitleChromaRepair>();
            owner.Initialize(shader);return owner;
        }
        public void Initialize(Shader shader)
        {
            if(shader==null || !shader.isSupported)throw new ArgumentException("A supported ChatOverlayChroma shader is required");
            replacement=shader;Bind();
        }
        void OnEnable(){Camera.onPreRender+=BeforeCamera;Camera.onPostRender+=AfterCamera;}
        void OnDisable()
        {
            Camera.onPreRender-=BeforeCamera;Camera.onPostRender-=AfterCamera;
            Shader.SetGlobalFloat(GlobalKey,0);Shader.SetGlobalFloat("_MGFRDepthCoverageAvailable",0);cameraKeyStack.Clear();cameraDepthStack.Clear();
            for(int i=0;i<materials.Count;i++)if(materials[i]!=null && materials[i].shader==replacement)materials[i].shader=previousShaders[i];
            materials.Clear();previousShaders.Clear();
        }
        void LateUpdate(){if(replacement!=null && (materials.Count<2 || materials.Exists(m=>m==null)) && Time.unscaledTime>=nextFind){nextFind=Time.unscaledTime+1;Bind();}}
        void Bind()
        {
            foreach(var overlay in FindObjectsByType<CameraChatOverlay>(FindObjectsInactive.Include,FindObjectsSortMode.None))
            foreach(var renderer in overlay.GetComponentsInChildren<MeshRenderer>(true))
            {
                Material material=renderer.sharedMaterial;
                if(material==null || materials.Contains(material))continue;
                if(material.shader==null || (material.shader.name!="MGFR/ChatOverlay" && material.shader!=replacement))continue;
                materials.Add(material);previousShaders.Add(material.shader);
                int queue=material.renderQueue;material.shader=replacement;material.renderQueue=queue;
                // Fixed renderer role; the overlay retains the exact Material and font atlas.
                material.SetFloat("_MGFRSubtitleOpaquePanel",renderer.name=="Transcript scrim"?1:0);
            }
        }
        public static bool IsKeyCamera(Camera camera)
        {
            if(camera==null || camera.clearFlags!=CameraClearFlags.SolidColor)return false;
            Color c=camera.backgroundColor;return c.r<.001f && c.g>.999f && c.b<.001f;
        }
        public void ConfigureForCamera(Camera camera){bool key=IsKeyCamera(camera);if(key)camera.depthTextureMode|=DepthTextureMode.Depth;Shader.SetGlobalFloat(GlobalKey,key?1:0);Shader.SetGlobalFloat("_MGFRDepthCoverageAvailable",key?1:0);}
        void BeforeCamera(Camera camera)
        {
            cameraKeyStack.Push(Shader.GetGlobalFloat(GlobalKey));cameraDepthStack.Push(Shader.GetGlobalFloat("_MGFRDepthCoverageAvailable"));ConfigureForCamera(camera);
        }
        void AfterCamera(Camera camera){Shader.SetGlobalFloat(GlobalKey,cameraKeyStack.Count>0?cameraKeyStack.Pop():0);Shader.SetGlobalFloat("_MGFRDepthCoverageAvailable",cameraDepthStack.Count>0?cameraDepthStack.Pop():0);}
    }
}
