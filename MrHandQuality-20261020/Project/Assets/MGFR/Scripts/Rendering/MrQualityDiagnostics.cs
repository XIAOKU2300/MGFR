using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;
using MGFR.Character;
using UnityEngine.SceneManagement;

namespace MGFR.Rendering
{
    public sealed class MrQualityDiagnostics : MonoBehaviour
    {
        public const string BuildId="MRHQ-20261020-r4-latest-structured-voice";
        readonly List<XRDisplaySubsystem> displays=new List<XRDisplaySubsystem>();
        float next; int lastFrame=-1;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if(SceneManager.GetActiveScene().name==SiCharacterBootstrap.SceneName)
                new GameObject("MR quality diagnostics").AddComponent<MrQualityDiagnostics>();
        }
        void Start(){Debug.Log("[MR quality] build="+BuildId+" cameraExposureTimestamp=unavailable recognitionConfidence=unavailable");}
        void OnEnable(){Camera.onPostRender+=Sample;}
        void OnDisable(){Camera.onPostRender-=Sample;}
        void Sample(Camera camera)
        {
            if(camera!=Camera.main||Time.unscaledTime<next||Time.frameCount==lastFrame)return;
            next=Time.unscaledTime+5;lastFrame=Time.frameCount;
            Debug.Log($"[MR quality] build={BuildId} active={MrMaterialPolicy.Active} materials={MrMaterialPolicy.MaterialCount} colorSpace={QualitySettings.activeColorSpace} configuredAA={QualitySettings.antiAliasing} cameraAA={camera.allowMSAA} hdr={camera.allowHDR} depth={camera.depthTextureMode} path={camera.actualRenderingPath} stereo={camera.stereoEnabled} pixels={camera.pixelWidth}x{camera.pixelHeight}");
            SubsystemManager.GetSubsystems(displays);bool actual=false;
            foreach(var display in displays)if(display.running)
            {
                for(int p=0;p<display.GetRenderPassCount();p++)
                {
                    display.GetRenderPass(p,out var pass);var desc=pass.renderTargetDesc;
                    for(int eye=0;eye<pass.GetRenderParameterCount();eye++)
                    {
                        pass.GetRenderParameter(camera,eye,out var param);actual=true;
                        Debug.Log($"[MR eye target] pass={p} eyeParameter={eye} texture={desc.width}x{desc.height} samples={desc.msaaSamples} dimension={desc.dimension} viewport={param.viewport} arraySlice={param.textureArraySlice} source=XRDisplaySubsystem.renderTargetDesc");
                    }
                }
            }
            if(!actual)Debug.Log("[MR eye target] actualXRTarget=unavailable; desktop/configuredAA is not eye-target evidence");
        }
    }
}
