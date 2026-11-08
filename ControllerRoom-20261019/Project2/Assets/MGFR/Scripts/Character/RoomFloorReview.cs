using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.Skins;
using MGFR.SmokeTest;
using MGFR.Wardrobe;
using UnityEngine;

namespace MGFR.Character
{
    public sealed class RoomFloorReview : MonoBehaviour
    {
        readonly List<string> checks = new List<string>();
        [Serializable] sealed class Report
        {
            public bool pass, headsetTested;
            public string mode = "PACKAGED_DESKTOP_PLACEMENT_AND_REFERENCE_SPACE_SEQUENCE_CHECK";
            public string[] checks;
            public int wardrobeParts;
            public float maxGroundError, maxAnchorDrift;
        }
        Report report = new Report();
        void Check(bool value, string label)
        { if (!value) throw new InvalidOperationException(label); checks.Add(label); }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "-mgfr-floor-review") >= 0)
                new GameObject("Floor placement packaged verification").AddComponent<RoomFloorReview>();
        }

        IEnumerator Start()
        {
            float end = Time.realtimeSinceStartup + 45;
            WardrobeLiveRuntime live;
            while ((live = WardrobeLiveRuntime.Instance) == null || !live.IsReady)
            { if (Time.realtimeSinceStartup > end) { Application.Quit(2); yield break; } yield return null; }
            yield return null;
            var args = Environment.GetCommandLineArgs();
            string folder = args[Array.IndexOf(args, "-mgfr-check-dir") + 1];
            Directory.CreateDirectory(folder);
            try { Run(live); report.pass = true; }
            catch (Exception error) { checks.Add("FAILED: " + error.Message); Debug.LogException(error); }
            report.checks = checks.ToArray();
            File.WriteAllText(Path.Combine(folder, "floor-placement.json"), JsonUtility.ToJson(report, true));
            Application.Quit(report.pass ? 0 : 1);
        }

        void Run(WardrobeLiveRuntime live)
        {
            Check(FindAnyObjectByType<MGFR.Dialogue.AutomaticVoiceSession>() == null, "review never records or sends microphone audio");
            report.wardrobeParts = live.Adapter.Profile.parts.Length;
            Check(report.wardrobeParts == 10 && ShoeFootPose.Instance.Ready && live.Cloth.IsReady,
                "complete wardrobe, independent shoes and cloth runtime remain present");
            Check(FindAnyObjectByType<RoomFloorPlacement>() != null, "scene installs floor placement runtime");

            var gate = new FloorPlacementGate();
            Check(!gate.Observe(0, false, false, false), "startup waits without tracking");
            Check(!gate.Observe(.5f, false, true, false), "device pose is not treated as calibrated floor");
            Check(!gate.Observe(1, true, true, true), "asynchronous floor switch waits for fresh pose");
            Check(!gate.Observe(1.2f, true, true, false), "floor origin settles before placement");
            Check(gate.Observe(1.4f, true, true, false) && gate.Measured, "stable floor places exactly once");
            Check(!gate.Observe(4, true, true, false), "head motion never requests another anchor");
            Check(!gate.Observe(5, true, false, false), "tracking loss keeps anchor");
            Check(!gate.Observe(6, true, true, false) && !gate.Observe(6.4f, true, true, false), "tracking recovery keeps anchor");
            Check(!gate.Observe(10, false, true, true) && !gate.Observe(20, false, true, false) && gate.Measured,
                "temporary loss of floor does not replace measured ground with estimated height");
            Check(!gate.Observe(21, true, true, true) && gate.Observe(21.4f, true, true, false), "runtime recenter waits then places on updated floor");
            gate.RequestPlacement();
            Check(!gate.Observe(22, true, true, false) && gate.Observe(22.4f, true, true, false), "explicit reposition waits for stable pose");
            var late = new FloorPlacementGate();
            Check(!late.Observe(0, false, true, false) && !late.Observe(7, false, true, false), "no premature estimated placement");
            Check(late.Observe(8.1f, false, true, false) && !late.Measured, "unsupported runtime fallback is marked estimated");
            Check(!late.Observe(9, true, true, true) && late.Observe(9.4f, true, true, false) && late.Measured,
                "late floor availability upgrades an estimated placement");

            var character = FindAnyObjectByType<SiCharacterController>();
            character.defaultScale = 1.17f; character.ResetPlacement();
            foreach (float ground in new[] { 0f, .42f, -.31f })
            foreach (float eyeHeight in new[] { 1.72f, .74f })
            foreach (float yaw in new[] { 0f, 90f, 213f })
            {
                var viewer = new Vector3(2.3f, ground + eyeHeight, -1.7f);
                var heading = Quaternion.Euler(0, yaw, 0) * Vector3.forward;
                var forward = Quaternion.Euler(-62f, yaw, 0) * Vector3.forward;
                character.PlaceOnGround(viewer, forward, 1.5f, ground);
                var expected = new Vector3(viewer.x, ground, viewer.z) + heading * 1.5f;
                Check(Vector3.Distance(character.transform.position, expected) < .0001f, "ground/head height/yaw placement " + checks.Count);
                Check(Vector3.Dot(-character.transform.forward, -heading) > .9999f, "model front faces player " + checks.Count);
                report.maxGroundError = Mathf.Max(report.maxGroundError, Mathf.Abs(character.GroundHeight - ground));
            }
            var fixedAnchor = character.transform.position;
            var head = FindAnyObjectByType<XrDeviceFollower>();
            for (int i = 0; i < 180; i++)
            {
                head.ApplyTrackedPose(new Vector3(i * .01f, 1.6f - i * .003f, .2f), Quaternion.Euler(0, i, 0));
                report.maxAnchorDrift = Mathf.Max(report.maxAnchorDrift, Vector3.Distance(character.transform.position, fixedAnchor));
            }
            Check(report.maxAnchorDrift < .00001f, "walking crouching and turning leave placed character fixed");
            character.ResetPlacement();
            Check(Vector3.Distance(character.transform.position, fixedAnchor) < .00001f && Mathf.Abs(character.CharacterScale - 1.17f) < .00001f,
                "Home reset preserves calibrated ground and current scale");
            character.PlaceOnGround(Vector3.zero, Vector3.up, 1.5f, .2f);
            Check(float.IsFinite(character.transform.position.sqrMagnitude), "vertical gaze has finite heading fallback");
        }
    }
}
