using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.Attention;
using MGFR.Character;
using MGFR.Experience;
using MGFR.PhysicsRig;
using MGFR.RenderStyles.ZmdEndfield;
using UnityEngine;

namespace MGFR.Rendering
{
    public sealed class MrEdgeReview : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "-mgfr-mr-edge-review") >= 0)
                new GameObject("MR edge actual render review").AddComponent<MrEdgeReview>();
        }
        IEnumerator Start()
        {
            string[] args = Environment.GetCommandLineArgs();
            int at = Array.IndexOf(args, "-mgfr-mr-edge-output");
            if (at < 0 || at + 1 >= args.Length) { Application.Quit(2); yield break; }
            string output = args[at + 1];
            Directory.CreateDirectory(output);
            ZmdRenderStyle style;
            float deadline = Time.realtimeSinceStartup + 90;
            while ((style = FindAnyObjectByType<ZmdRenderStyle>()) == null || !style.IsReady)
            {
                if (Time.realtimeSinceStartup > deadline) { Debug.LogError("MR edge review timed out"); Application.Quit(3); yield break; }
                yield return null;
            }
            yield return new WaitForSeconds(2);
            var loader = style.Loader;
            var idle = FindAnyObjectByType<IdleMotionPlayer>();
            if (idle != null) { idle.ManualTime = .9f; yield return null; idle.enabled = false; }
            var physics = FindAnyObjectByType<PmxSecondaryPhysics>(); if (physics != null) physics.enabled = false;
            var legs = FindAnyObjectByType<LegPlantSolver>(); if (legs != null) legs.enabled = false;
            var face = FindAnyObjectByType<FaceAttentionController>(); if (face != null) face.AutoUpdate = false;
            var control = FindAnyObjectByType<SiCharacterController>(); if (control != null) control.enabled = false;
            for (int i = 0; i < loader.Renderer.sharedMesh.blendShapeCount; i++) loader.Renderer.SetBlendShapeWeight(i, 0);

            var guard = FindAnyObjectByType<MrChromaEdgeGuard>();
            guard.SetRequested(false);
            QualitySettings.antiAliasing = 4; Camera.main.allowMSAA = true;
            guard.SetRequested(true);
            bool applied = guard.Applied && !Camera.main.allowMSAA && QualitySettings.antiAliasing == 0;
            guard.SetRequested(false);
            bool restored = !guard.Applied && Camera.main.allowMSAA && QualitySettings.antiAliasing == 4;
            Camera.main.backgroundColor = Color.gray; guard.SetRequested(true);
            bool backgroundGate = !guard.Applied && Camera.main.allowMSAA && QualitySettings.antiAliasing == 4;
            Camera.main.backgroundColor = Color.green;
            guard.enabled = false;

            int originalLayer = loader.gameObject.layer; loader.gameObject.layer = 8;
            var camera = new GameObject("Fixed MR edge capture camera").AddComponent<Camera>();
            camera.CopyFrom(Camera.main); camera.enabled = false;
            camera.stereoTargetEye = StereoTargetEyeMask.None; camera.cullingMask = 1 << 8;
            camera.backgroundColor = Color.green; camera.clearFlags = CameraClearFlags.SolidColor;
            const int width = 1200, height = 1600;
            camera.aspect = width / (float)height;
            var image = new Texture2D(width, height, TextureFormat.RGB24, false);
            var views = new[] { new Vector3(0, .92f, -2.65f), new Vector3(0, 1.51f, -.75f), new Vector3(.6f, 1.5f, -.8f) };
            var aims = new[] { Vector3.up * .90f, Vector3.up * 1.49f, Vector3.up * 1.49f };
            var names = new[] { "fullbody", "face", "threequarter" };
            var checks = new List<string> { "source=ACTUAL_UNITY_RENDER_NOT_HEADSET", "guardApplied=" + applied,
                "restoresAA=" + restored, "nonGreenCameraPreserved=" + backgroundGate };
            bool green = true; int magenta = 0;
            for (int view = 0; view < views.Length; view++)
            {
                camera.transform.position = loader.transform.TransformPoint(views[view]);
                camera.transform.LookAt(loader.transform.TransformPoint(aims[view]));
                camera.fieldOfView = view == 0 ? 43 : 34;
                for (int mode = 0; mode < 2; mode++)
                {
                    int aa = mode == 0 ? 4 : 1;
                    camera.allowMSAA = mode == 0;
                    var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32) { antiAliasing = aa };
                    rt.Create(); camera.targetTexture = rt;
                    camera.Render(); var previous = RenderTexture.active; RenderTexture.active = rt;
                    image.ReadPixels(new Rect(0, 0, width, height), 0, 0); image.Apply(); RenderTexture.active = previous;
                    File.WriteAllBytes(Path.Combine(output, names[view] + (mode == 0 ? "-before.png" : "-after.png")), image.EncodeToPNG());
                    Color c = image.GetPixel(0, 0); green &= c.g > .999f && c.r < .001f && c.b < .001f;
                    foreach (Color32 p in image.GetPixels32()) if (p.r > 240 && p.g < 15 && p.b > 240) magenta++;
                    camera.targetTexture = null; rt.Release(); Destroy(rt);
                }
                yield return null;
            }
            loader.gameObject.layer = originalLayer;
            checks.Add("pureGreenBackground=" + green); checks.Add("magentaPixels=" + magenta);
            bool pass = applied && restored && backgroundGate && green && magenta == 0;
            checks.Add("pass=" + pass); File.WriteAllLines(Path.Combine(output, "runtime-checks.txt"), checks);
            Debug.Log("[MR edge review] " + string.Join(" ", checks));
            Destroy(image); Destroy(camera.gameObject); Application.Quit(pass ? 0 : 1);
        }
    }
}
