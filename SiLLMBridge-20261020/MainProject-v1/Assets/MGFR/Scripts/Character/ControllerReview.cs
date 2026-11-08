using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using MGFR.BareHands;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Skins;
using MGFR.Wardrobe;
using UnityEngine;

namespace MGFR.Character
{
    public sealed class ControllerReview : MonoBehaviour
    {
        [Serializable] sealed class Report
        {
            public bool pass, headsetTested, microphoneUsed;
            public string mode = "PACKAGED_DESKTOP_CONTROLLER_SAMPLES_AND_GRIP_PROXY_NOT_HARDWARE";
            public string[] checks;
            public int parts, glyphVertices;
        }
        readonly List<string> checks = new List<string>();
        readonly Report report = new Report();
        ControllerActions actions;
        WardrobeLiveRuntime live;
        ControllerGripSource grip;
        IdleMotionPlayer idle;
        ShoeFootPose foot;
        LegPlantSolver legs;
        string folder;
        Vector3 last;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (Array.IndexOf(Environment.GetCommandLineArgs(), "-mgfr-controller-review") >= 0)
                new GameObject("Packaged controller review").AddComponent<ControllerReview>();
        }
        void Check(bool pass, string text)
        { if (!pass) throw new InvalidOperationException(text); checks.Add(text); }
        IEnumerator Start()
        {
            var args = Environment.GetCommandLineArgs();
            folder = args[Array.IndexOf(args, "-mgfr-check-dir") + 1]; Directory.CreateDirectory(folder);
            float end = Time.realtimeSinceStartup + 45;
            while ((live = WardrobeLiveRuntime.Instance) == null || !live.IsReady || ControllerActions.Instance == null || ControllerActions.Instance.View == null)
            { if (Time.realtimeSinceStartup > end) { Application.Quit(2); yield break; } yield return null; }
            yield return null;
            actions = ControllerActions.Instance; actions.Manual = true;
            grip = ControllerGripSource.Instance; grip.Manual = true;
            FindAnyObjectByType<SiCharacterBootstrap>().enabled = false;
            var camera = Camera.main;
            camera.transform.parent.SetPositionAndRotation(new Vector3(0, 1.6f, -1.8f), Quaternion.identity);
            camera.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
            FindAnyObjectByType<CameraChatOverlay>().SetVisible(false);
            try { Controls(); ProxyInteraction(); }
            catch (Exception error) { checks.Add("FAILED: " + error.Message); Debug.LogException(error); Finish(false); yield break; }
            actions.Character.RestoreRoomPlacement(Vector3.zero, 0, 1, 0);
            if (actions.MenuOpen) Step(b: true);
            Step(); Step(y: true); Step();
            yield return null;
            yield return new WaitForEndOfFrame();
            Capture("controller-menu.png");
            try { Check(actions.View.Shown && actions.View.GlyphVertices > 100, "binocular mesh menu renders Chinese labels and current actions"); }
            catch (Exception error) { checks.Add("FAILED: " + error.Message); Finish(false); yield break; }
            report.glyphVertices = actions.View.GlyphVertices;
            Finish(true);
        }
        void Step(Vector2 left = default, Vector2 right = default, bool y = false, bool a = false, bool b = false, bool x = false, bool tracked = true)
        {
            actions.Step(new ControllerButtons { LeftTracked = tracked, RightTracked = tracked, LeftStick = left, RightStick = right,
                X = x, Y = y, A = a, B = b }, 1f / 60);
        }
        void BeginPlacement()
        {
            Step(); Step(y: true); Step(); Step(a: true); Step();
            Check(actions.Placing && !actions.MenuOpen, "A enters placement without a trigger action " + checks.Count);
        }
        void Controls()
        {
            Check(FindAnyObjectByType<AutomaticVoiceSession>() == null, "review never starts microphone capture");
            report.parts = live.Adapter.Profile.parts.Length;
            Check(report.parts == 10 && live.Cloth.IsReady && ShoeFootPose.Instance.Ready, "all clothing, shoes and cloth components remain ready");
            var character = actions.Character; character.enabled = false;
            character.RestoreRoomPlacement(Vector3.zero, 0, 1, .23f); character.RememberRoomPlacement();
            var initial = character.transform.position;
            Step(); for (int i = 0; i < 30; i++) Step(left: Vector2.one, right: Vector2.one);
            Check(Vector3.Distance(initial, character.transform.position) < .00001f, "ordinary interaction ignores stick movement");
            Step(y: true); for (int i = 0; i < 8; i++) Step(y: true);
            Check(actions.MenuOpen, "held Y opens menu once");
            Step(); Step(a: true); Step();
            Check(actions.Placing, "menu action starts room adjustment");
            for (int i = 0; i < 30; i++) Step(left: Vector2.one * .1f, right: Vector2.one * .1f);
            Check(Vector3.Distance(initial, character.transform.position) < .00001f, "stick deadzone prevents drifting");
            for (int i = 0; i < 60; i++) Step(left: Vector2.up);
            Check(Mathf.Abs(character.transform.position.z - .35f) < .0001f && Mathf.Abs(character.GroundHeight - .23f) < .0001f,
                "left stick moves character along viewer ground plane at 0.35m/s");
            for (int i = 0; i < 30; i++) Step(right: Vector2.right);
            Check(Mathf.Abs(character.Yaw - 30) < .001f, "right stick turns character at 60deg/s");
            for (int i = 0; i < 30; i++) Step(right: Vector2.up);
            Check(Mathf.Abs(character.CharacterScale - 1.125f) < .001f, "right stick scales smoothly");
            for (int i = 0; i < 30; i++) Step(right: Vector2.up, x: true);
            Check(Mathf.Abs(character.GroundHeight - .26f) < .001f && Mathf.Abs(character.CharacterScale - 1.125f) < .001f,
                "X modifier adjusts height separately from scale");
            Step(b: true);
            Check(!actions.Placing && Vector3.Distance(character.transform.position, initial) < .00001f && character.Yaw == 0 && character.CharacterScale == 1,
                "B cancels position, turn, scale and height together");
            BeginPlacement(); for (int i = 0; i < 30; i++) Step(left: Vector2.right);
            Step(a: true); var saved = character.transform.position; character.ResetPlacement();
            Check(!actions.Placing && Vector3.Distance(saved, character.transform.position) < .00001f && saved.x > .17f,
                "A commits placement and Home keeps the saved ground anchor");
            BeginPlacement(); Step(tracked: false); var lost = character.transform.position;
            for (int i = 0; i < 30; i++) Step(left: Vector2.up);
            Check(Vector3.Distance(lost, character.transform.position) < .00001f, "tracking recovery requires neutral sticks before movement");
            Step(); Step(left: Vector2.up);
            Check(character.transform.position.z > lost.z, "neutral sticks rearm movement after reconnect");
            Step(b: true); Step();
            Step(tracked: false); Step(y: true); Step(y: true);
            Check(!actions.MenuOpen, "held menu button on reconnect does not activate");
            Step(); Step(y: true); Step();
            var menuPosition = character.transform.position;
            for (int i = 0; i < 4; i++) Step(right: Vector2.down);
            Check(actions.Selected == 1 && Vector3.Distance(menuPosition, character.transform.position) < .00001f,
                "menu navigation consumes sticks without moving character");
            Step(); Step(right: Vector2.up); Step(); Step(b: true); Step();
            bool captions = FindAnyObjectByType<CameraChatOverlay>().Visible;
            actions.Activate(4); Check(FindAnyObjectByType<CameraChatOverlay>().Visible != captions, "menu toggles subtitles"); actions.Activate(4);
            var motion = FindAnyObjectByType<IdleMotionPlayer>(); bool natural = motion.NaturalIdle;
            actions.Activate(5); Check(motion.NaturalIdle != natural, "menu toggles natural idle"); actions.Activate(5);
            actions.Activate(6); Check(!live.Enabled, "menu disables wardrobe interaction"); actions.Activate(6); Check(live.Enabled, "menu reenables wardrobe interaction");
            var skin = FindAnyObjectByType<SiSkinSwitcher>(); string original = skin.CurrentId;
            actions.Activate(2); Check(skin.CurrentId != original, "menu switches full skin");
            actions.Activate(2); Check(skin.CurrentId == original, "menu restores full skin"); live.Step(1f / 60);
            var mode = grip.Mode; actions.Activate(8); Check(grip.Mode != mode, "menu cycles automatic, controller and bare hand input"); grip.Mode = mode;
            character.RestoreRoomPlacement(Vector3.zero, 33, 1, 0); character.RememberRoomPlacement();
            Check(ControllerActions.Deadzone(float.NaN) == 0, "invalid axis values cannot move character");
        }
        void ProxyInteraction()
        {
            live.Manual = live.Cloth.Manual = true;
            foot = ShoeFootPose.Instance; foot.Manual = true;
            idle = FindAnyObjectByType<IdleMotionPlayer>(); idle.enabled = false;
            legs = FindAnyObjectByType<LegPlantSolver>(); legs.enabled = false;
            live.Hands.enabled = live.Hands.Physics.enabled = false;
            Check(!grip.UpdateGrip(0, .9f, false), "controller held on connect must be released before grabbing");
            Check(!grip.UpdateGrip(0, 0, false) && grip.UpdateGrip(0, .9f, false), "fresh trigger press arms controller grasp");
            Check(!grip.UpdateGrip(0, .9f, true) && !grip.UpdateGrip(0, .9f, false), "placement suppression requires release before the next grasp");
            last = live.Socket("shoe_left", 4);
            for (int i = 0; i < 24; i++) Pump(last, false);
            foreach (string id in new[] { "shoe_left", "shoe_right", "cover_skirt" })
            {
                int anchor = id == "shoe_left" ? 4 : id == "shoe_right" ? 2 : 0;
                Move(live.Socket(id, anchor), false); for (int i = 0; i < 4; i++) Pump(last, false);
                for (int i = 0; i < 4; i++) Pump(last, true);
                Check(live.Pending(0) == id, "controller grip acquires visible " + id);
                var part = live.Adapter.GetPart(id);
                var direction = live.Hands.Physics.Loader.transform.TransformVector(new Vector3(part.pullDirectionLocal[0], part.pullDirectionLocal[1], part.pullDirectionLocal[2]));
                Move(last + direction * part.pullDistanceMetres * 1.6f, true, 18);
                Check(live.Held(0) == id && !live.IsEquipped(id), "controller pull detaches " + id);
                var beforeMove = actions.Character.transform.position;
                actions.Activate(0);
                Check(!actions.Placing && Vector3.Distance(beforeMove, actions.Character.transform.position) < .00001f,
                    "held item prevents entering character adjustment " + id);
                for (int i = 0; i < 4; i++) Pump(last, false);
                Check(live.Held(0) == null, "controller release drops " + id);
                Move(live.DroppedAnchor(id, 1), false); for (int i = 0; i < 4; i++) Pump(last, true);
                Check(live.Held(0) == id, "controller picks up dropped " + id);
                Move(live.HeldSocket(0), true); for (int i = 0; i < 4; i++) Pump(last, false);
                Check(live.IsEquipped(id), "controller restores " + id);
                for (int i = 0; i < 16; i++) Pump(last, false);
            }
            actions.Activate(7); live.Step(1f / 60);
            Check(live.IsEquipped("cover_skirt") && live.IsEquipped("shoe_left") && live.IsEquipped("shoe_right"), "menu restores complete clothing and shoes");
        }
        void Pump(Vector3 point, bool pressed)
        {
            last = point; const float dt = 1f / 60;
            idle.Apply(.9f, dt); foot.Tick(dt); legs.SolveNow();
            bool pinch = grip.UpdateGrip(0, pressed ? 1 : 0, false);
            var rotation = Quaternion.Euler(0, 27, -12);
            var pose = new Pose(point - rotation * ControllerGripSource.PinchOffset, rotation);
            live.Hands.Source.PublishControllerFrame(0, ControllerGripSource.MakeFrame(pose, 0, pinch), true);
            live.Hands.Source.PublishControllerFrame(1, null, false);
            live.Hands.StepInteraction(dt); live.Step(dt); live.Cloth.Tick(dt); live.Hands.AcquireAfterPhysics();
            if (live.OwnsHand(0) && live.Hands.GrabbedBody[0] >= 0) throw new Exception("controller grip has two owners");
        }
        void Move(Vector3 point, bool pressed, int count = 16)
        { var start = last; for (int i = 1; i <= count; i++) Pump(Vector3.Lerp(start, point, i / (float)count), pressed); }
        void Capture(string name)
        {
            var camera = Camera.main; var old = camera.targetTexture; var active = RenderTexture.active;
            var rt = new RenderTexture(1500, 1000, 24); camera.targetTexture = rt;
            camera.backgroundColor = new Color(.22f, .25f, .29f); camera.Render(); RenderTexture.active = rt;
            var image = new Texture2D(1500, 1000, TextureFormat.RGB24, false); image.ReadPixels(new Rect(0, 0, 1500, 1000), 0, 0); image.Apply();
            File.WriteAllBytes(Path.Combine(folder, name), image.EncodeToPNG());
            camera.targetTexture = old; RenderTexture.active = active; rt.Release(); Destroy(rt); Destroy(image);
        }
        void Finish(bool pass)
        {
            report.pass = pass; report.checks = checks.ToArray();
            File.WriteAllText(Path.Combine(folder, "controller-check.json"), JsonUtility.ToJson(report, true));
            Application.Quit(pass ? 0 : 1);
        }
    }
}
