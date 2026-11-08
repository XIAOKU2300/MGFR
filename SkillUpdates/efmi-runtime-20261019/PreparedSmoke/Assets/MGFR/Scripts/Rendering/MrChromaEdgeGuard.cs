using System;
using MGFR.Character;
using MGFR.SmokeTest;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.XR;

namespace MGFR.Rendering
{
    // RGB keying cannot undo foreground/background colour mixing in MSAA resolves.
    // Apply before rendering, after the optional render styles initialise.
    [DefaultExecutionOrder(32000)]
    public sealed class MrChromaEdgeGuard : MonoBehaviour
    {
        public bool Requested { get; private set; } = true;
        public bool Applied { get; private set; }
        Camera ownedCamera;
        int previousAA;
        bool previousCameraAA;
        static bool Has(string flag) => Array.IndexOf(Environment.GetCommandLineArgs(), flag) >= 0;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (Has("-mgfr-mr-clean-edge") && SceneManager.GetActiveScene().name == SiCharacterBootstrap.SceneName)
                new GameObject("MR chroma edge guard (F10 compare)").AddComponent<MrChromaEdgeGuard>();
        }

        void OnEnable() { Camera.onPreCull += BeforeCamera; }
        void OnDisable() { Camera.onPreCull -= BeforeCamera; Restore(); }
        void Update()
        {
            if (Input.GetKeyDown(KeyCode.F10)) SetRequested(!Requested);
        }
        void LateUpdate() { Refresh(); }
        void BeforeCamera(Camera camera) { if (camera == Camera.main) Refresh(); }
        public void SetRequested(bool value) { Requested = value; Refresh(); }

        public static bool IsKeyCamera(Camera camera)
        {
            if (camera == null || camera.clearFlags != CameraClearFlags.SolidColor) return false;
            Color c = camera.backgroundColor;
            return c.r < .001f && c.g > .999f && c.b < .001f;
        }

        public void Refresh()
        {
            Camera camera = Camera.main;
            bool room = (!XrDeviceFollower.Suppressed && XRSettings.isDeviceActive) || Has("-mgfr-mr-edge-force");
            bool apply = Requested && room && IsKeyCamera(camera);
            if (Applied && (!apply || camera != ownedCamera)) Restore();
            if (!apply) return;
            if (!Applied)
            {
                ownedCamera = camera;
                previousAA = QualitySettings.antiAliasing;
                previousCameraAA = camera.allowMSAA;
                Applied = true;
                Debug.Log("[MGFR MR edge] ON: no green/foreground MSAA mixing. F10 compares original.");
            }
            // Both are required: allowMSAA alone need not control the XR eye target.
            QualitySettings.antiAliasing = 0;
            camera.allowMSAA = false;
        }

        void Restore()
        {
            if (!Applied) return;
            // Do not undo a different owner changing the global quality setting.
            if (QualitySettings.antiAliasing == 0) QualitySettings.antiAliasing = previousAA;
            if (ownedCamera != null) ownedCamera.allowMSAA = previousCameraAA;
            ownedCamera = null;
            Applied = false;
            Debug.Log("[MGFR MR edge] OFF: previous camera/AA settings restored.");
        }
    }
}
