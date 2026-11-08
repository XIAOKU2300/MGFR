using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.Attention;
using MGFR.BareHands;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Wardrobe;
using UnityEngine;
using UnityEngine.XR.Hands;

namespace MGFR.Character
{
    public sealed class HandCoexistReview : MonoBehaviour
    {
        [Serializable] sealed class Report
        {
            public bool pass, headsetTested, microphoneUsed;
            public string mode = "PACKAGED_NATIVE_SAMPLE_ROUTING_AND_BINOCULAR_OCCLUSION_NOT_HEADSET";
            public string[] checks;
            public int leftEyePixels, rightEyePixels, behindPixels;
        }
        readonly Report report = new Report();
        readonly List<string> checks = new List<string>();
        BareHandInteraction hands;
        ControllerGripSource driver;
        HandJointSource source;
        string folder;
        double clock;
        void Check(bool value, string text)
        { if (!value) throw new InvalidOperationException(text); checks.Add(text); }
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "-mgfr-coexist-review") >= 0)
                new GameObject("Real hand and controller coexistence review").AddComponent<HandCoexistReview>();
        }
        IEnumerator Start()
        {
            var args = Environment.GetCommandLineArgs(); folder = args[Array.IndexOf(args, "-mgfr-check-dir") + 1]; Directory.CreateDirectory(folder);
            float end = Time.realtimeSinceStartup + 45;
            while (WardrobeLiveRuntime.Instance == null || !WardrobeLiveRuntime.Instance.IsReady)
            { if (Time.realtimeSinceStartup > end) { Application.Quit(2); yield break; } yield return null; }
            yield return null;
            try { Run(); report.pass = true; }
            catch (Exception error) { checks.Add("FAILED: " + error.Message); Debug.LogException(error); }
            report.checks = checks.ToArray();
            File.WriteAllText(Path.Combine(folder, "hand-coexist.json"), JsonUtility.ToJson(report, true));
            Application.Quit(report.pass ? 0 : 1);
        }
        void Run()
        {
            Check(FindAnyObjectByType<AutomaticVoiceSession>() == null, "review never starts microphone capture");
            var live = WardrobeLiveRuntime.Instance; live.Manual = live.Cloth.Manual = true;
            hands = live.Hands; hands.enabled = hands.Physics.enabled = false;
            source = hands.Source; source.enabled = false;
            source.Replay = false;
            driver = ControllerGripSource.Instance; driver.Manual = true;
            ControllerActions.Instance.Manual = true;
            FindAnyObjectByType<SiCharacterBootstrap>().enabled = false;
            var loader = hands.Physics.Loader; var root = loader.transform;
            FindAnyObjectByType<SiCharacterController>().RestoreRoomPlacement(Vector3.zero, 0, 1, 0);
            var idle = FindAnyObjectByType<IdleMotionPlayer>(); idle.enabled = false; idle.Apply(.9f);
            ShoeFootPose.Instance.Manual = true; ShoeFootPose.Instance.Tick(1f / 60);
            var legs = FindAnyObjectByType<LegPlantSolver>(); legs.enabled = false; legs.SolveNow();
            FindAnyObjectByType<FaceAttentionController>().AutoUpdate = false;
            hands.DebugHands = false; hands.OcclusionEnabled = true;

            source.UseControllerPose(0, true); source.UseControllerPose(1, true);
            var proxy = new Pose(root.TransformPoint(new Vector3(1.2f, 1.2f, 1)), Quaternion.identity);
            source.PublishControllerFrame(0, ControllerGripSource.MakeFrame(proxy, 0, false), true);
            source.PublishControllerFrame(1, ControllerGripSource.MakeFrame(proxy, 1, false), true);
            Vector3 beforeProxy = source.Frames[0].PinchPoint;
            var front = root.TransformPoint(new Vector3(0, 1.1f, -.48f));
            int samples = source.PhysicsSamples;
            Native(0, front, false);
            Check(source.PhysicsSamples == samples + 1 && source.NativeFrames[0].Tracked && source.RenderFrames[0].Tracked,
                "native physics and render samples continue while both controllers drive interaction");
            Check(Vector3.Distance(source.Frames[0].PinchPoint, beforeProxy) < .00001f,
                "native render pose does not teleport an active controller grasp");
            Check(Vector3.Distance(source.RenderFrames[0].PinchPoint, front) < .00001f,
                "occlusion uses measured native fingers instead of the controller proxy");
            var realTip = source.RenderFrames[0].PinchPoint;
            source.PublishControllerFrame(1, null, false);
            Check(source.RenderFrames[0].Tracked && Vector3.Distance(realTip, source.RenderFrames[0].PinchPoint) < .00001f,
                "a lost controller cannot erase native hand render data");

            driver.Mode = ControllerInteractionMode.Auto; driver.UpdateRouting(true, true);
            Check(!source.IsControllerPose(0) && source.IsControllerPose(1) && source.Frames[0].Tracked,
                "automatic mode prefers native left hand and keeps right controller independently");
            hands.StepInteraction(1f / 60);
            Check(hands.DepthMeshes[0].Object.activeSelf && !hands.DepthMeshes[1].Object.activeSelf,
                "real hand passthrough remains active with another controller connected");
            Check(!ControllerGripSource.WantsController(ControllerInteractionMode.Auto, true, true, false, false),
                "controller presence alone never replaces a valid real hand");
            Check(ControllerGripSource.WantsController(ControllerInteractionMode.Auto, true, true, true, true),
                "an existing controller grab remains attached until release");

            driver.Mode = ControllerInteractionMode.Controller; driver.UpdateRouting(true, true);
            Native(0, front, false); source.PublishControllerFrame(0, ControllerGripSource.MakeFrame(proxy, 0, false), true);
            source.PublishControllerFrame(1, ControllerGripSource.MakeFrame(proxy, 1, false), true);
            hands.StepInteraction(1f / 60);
            Check(source.ControllerDriven && hands.DepthMeshes[0].Object.activeSelf,
                "explicit controller mode also preserves measured hand passthrough");

            loader.gameObject.layer = 8;
            foreach (var mesh in hands.DepthMeshes) mesh.Object.layer = 9;
            var camera = new GameObject("Hand coexistence pixel camera").AddComponent<Camera>();
            camera.CopyFrom(Camera.main); camera.enabled = false; camera.cullingMask = (1 << 8) | (1 << 9);
            camera.stereoTargetEye = StereoTargetEyeMask.None; camera.fieldOfView = 42;
            camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(0, 1, 0, 1);
            var rt = new RenderTexture(900, 900, 24); camera.targetTexture = rt;
            var image = new Texture2D(900, 900, TextureFormat.RGB24, false);
            for (int eye = 0; eye < 2; eye++)
            {
                camera.transform.SetPositionAndRotation(root.TransformPoint(new Vector3(eye == 0 ? -.032f : .032f, 1.1f, -1.8f)), root.rotation);
                Native(0, front, false); hands.OcclusionEnabled = false; hands.StepInteraction(1f / 60);
                byte[] baseline = Render(camera, rt, image, "eye" + eye + "-baseline.png");
                hands.OcclusionEnabled = true; hands.StepInteraction(1f / 60);
                byte[] visible = Render(camera, rt, image, "eye" + eye + "-real-hand-with-controller.png");
                int cut = GreenChanges(baseline, visible);
                if (eye == 0) report.leftEyePixels = cut; else report.rightEyePixels = cut;
                Check(cut > 200 && visible[0] == 0 && visible[1] == 255 && visible[2] == 0,
                    "eye " + eye + " reveals real hand in front of character while controllers remain active");
                Native(0, root.TransformPoint(new Vector3(0, 1.1f, 1.5f)), false); hands.StepInteraction(1f / 60);
                report.behindPixels += GreenChanges(baseline, Render(camera, rt, image, "eye" + eye + "-hand-behind.png"));
            }
            Check(report.behindPixels < 30, "real hand behind character does not cut through foreground");
            camera.targetTexture = null; rt.Release(); Destroy(rt); Destroy(image); Destroy(camera.gameObject);

            source.AcceptSample(0, new HandFrame(), XRHandSubsystem.UpdateType.Dynamic, clock += .02);
            hands.StepInteraction(1f / 60);
            Check(!hands.DepthMeshes[0].Object.activeSelf && source.Frames[0].Tracked,
                "native tracking loss hides stale silhouette and keeps controller interaction alive");
            Native(0, front, true);
            driver.Mode = ControllerInteractionMode.Auto; driver.UpdateRouting(true, true);
            Check(!source.IsControllerPose(0) && source.Frames[0].CanStartPinch, "native reacquisition restores observed fingers without a mode switch");
            var pinch = new HandPinchState();
            pinch.Update(source.Frames[0], .0167f);
            Check(pinch.Update(source.Frames[0], .0167f), "real native pinch samples still reach gesture recognition");
            hands.StepInteraction(.0167f); hands.StepInteraction(.0167f);
            Check(hands.Pinching[0] && hands.DepthMeshes[0].Object.activeSelf,
                "native pinch interaction and passthrough operate together after controller handoff");
            driver.Mode = ControllerInteractionMode.BareHands; driver.UpdateRouting(true, true);
            Check(!source.IsControllerPose(0) && !source.IsControllerPose(1), "explicit bare hand mode leaves both native inputs available");
        }
        void Native(int hand, Vector3 point, bool pinch)
        {
            var positions = PoseAt(point, pinch);
            var frame = new HandFrame { Tracked = true, Timestamp = Time.unscaledTime, ValidCount = 26, ObservedCount = 26 };
            for (int i = 0; i < 26; i++)
            { frame.Joints[i] = positions[i]; frame.Valid[i] = frame.Observed[i] = true; frame.Radius[i] = i < 2 ? .018f : .008f; }
            source.AcceptSample(hand, frame, XRHandSubsystem.UpdateType.Dynamic, clock += .02);
        }
        static Pose[] PoseAt(Vector3 point, bool pinch)
        {
            var local = new Vector3[26]; local[1] = new Vector3(0, -.05f, 0);
            local[2] = new Vector3(-.035f, -.025f, 0); local[3] = new Vector3(-.05f, 0, 0);
            local[4] = new Vector3(-.06f, .025f, 0); local[5] = new Vector3(-.065f, .05f, 0);
            for (int finger = 0; finger < 4; finger++) for (int j = 0; j < 5; j++) local[6 + finger * 5 + j] = new Vector3(-.03f + finger * .02f, .012f + j * .023f, 0);
            if (pinch) { local[5] = local[10] + new Vector3(-.009f, 0, -.003f); local[4] = (local[3] + local[5]) * .5f; }
            var offset = (local[5] + local[10]) * .5f; var poses = new Pose[26];
            for (int i = 0; i < 26; i++) poses[i] = new Pose(point + local[i] - offset, Quaternion.identity);
            return poses;
        }
        byte[] Render(Camera camera, RenderTexture target, Texture2D image, string filename)
        {
            var previous = RenderTexture.active; camera.Render(); RenderTexture.active = target;
            image.ReadPixels(new Rect(0, 0, 900, 900), 0, 0); image.Apply(); RenderTexture.active = previous;
            File.WriteAllBytes(Path.Combine(folder, filename), image.EncodeToPNG());
            return image.GetRawTextureData<byte>().ToArray();
        }
        static int GreenChanges(byte[] before, byte[] after)
        {
            int count = 0;
            for (int i = 0; i < before.Length; i += 3)
                if (after[i] == 0 && after[i + 1] == 255 && after[i + 2] == 0 && (before[i] != 0 || before[i + 1] != 255 || before[i + 2] != 0)) count++;
            return count;
        }
    }
}
