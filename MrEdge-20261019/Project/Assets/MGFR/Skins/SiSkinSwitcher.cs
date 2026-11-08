using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;
using MGFR.Experience;
using MGFR.Attention;
using MGFR.BareHands;
using MGFR.PhysicsRig;
using MGFR.RenderStyles.ZmdEndfield;

namespace MGFR.Skins
{
    [DefaultExecutionOrder(-2000)]
    public sealed class SiSkinSwitcher : MonoBehaviour
    {
        public bool IsReady { get; private set; }
        public string CurrentId { get; private set; } = "original";
        public string Status { get; private set; } = "正在准备皮肤…";
        public int SwitchCount { get; private set; }
        public ZmdRenderStyle Style { get; private set; }
        public SiCharacterLoader Loader => Style.Loader;
        public SiAppearance CurrentAppearance => appearances[CurrentId];
        readonly Dictionary<string, SiAppearance> appearances = new Dictionary<string, SiAppearance>();
        readonly List<SiCharacterLoader> stagingLoaders = new List<SiCharacterLoader>();
        BareHandInteraction hands;
        PmxSecondaryPhysics physics;
        IdleMotionPlayer idle;
        Font font;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (SceneManager.GetActiveScene().name == SiCharacterBootstrap.SceneName &&
                Array.IndexOf(Environment.GetCommandLineArgs(), "-mgfr-skins") >= 0)
                new GameObject("MGFR runtime skin selection").AddComponent<SiSkinSwitcher>();
        }
        IEnumerator Start()
        {
            while ((Style = FindAnyObjectByType<ZmdRenderStyle>()) == null || !Style.IsReady ||
                (hands = FindAnyObjectByType<BareHandInteraction>()) == null || !hands.IsReady)
                yield return null;
            physics = hands.Physics; idle = FindAnyObjectByType<IdleMotionPlayer>();
            appearances.Add("original", Style.OriginalAppearance);
            Style.SkinSwitchingEnabled = true;
            Style.SetActive(Style.Active);
            font = Font.CreateDynamicFontFromOSFont("Microsoft YaHei", 17);
            IsReady = true; Status = "F5 切换皮肤 · F11 切换渲染";
            var args = Environment.GetCommandLineArgs(); int at = Array.IndexOf(args, "-mgfr-skin");
            if (at >= 0 && at + 1 < args.Length) TrySelect(args[at + 1]);
        }
        void Update()
        {
            if (IsReady && Input.GetKeyDown(KeyCode.F5))
                TrySelect(CurrentId == "original" ? "swimsuit" : "original");
        }
        public bool TrySelect(string id)
        {
            if (!IsReady || id == CurrentId) return IsReady;
            if (id != "original" && id != "swimsuit") { Status = "未知皮肤"; return false; }
            // Validate and allocate the complete target before touching the live rig.
            try
            {
                if (!appearances.ContainsKey(id))
                {
                    string root = Path.Combine(Application.streamingAssetsPath, "skins", "si-swimsuit-barefoot-ankle-v4");
                    var staging = new GameObject("Cached skin resources " + id);
                    staging.SetActive(false); staging.transform.SetParent(transform, false);
                    var candidate = staging.AddComponent<SiCharacterLoader>();
                    candidate.buildOnStart = false; candidate.dataRootOverride = root; candidate.logMaterialTable = false;
                    candidate.Build(); stagingLoaders.Add(candidate);
                    if (!candidate.IsReady) throw new InvalidDataException(candidate.Status);
                    var appearance = candidate.CaptureAppearance(id);
                    appearance.ValidateAgainst(Loader.Data);
                    appearances.Add(id, appearance);
                }
            }
            catch (Exception error)
            {
                Status = "皮肤加载失败，保留当前皮肤";
                Debug.LogError("[MGFR skins] " + error.GetType().Name + ": " + error.Message);
                return false;
            }
            var previous = CurrentAppearance; var target = appearances[id];
            var bones = Loader.Renderer.bones;
            var rotations = new Quaternion[bones.Length]; var deltas = new Vector3[bones.Length];
            var blend = new float[Loader.Renderer.sharedMesh.blendShapeCount];
            for (int i = 0; i < bones.Length; i++)
            {
                rotations[i] = bones[i].localRotation;
                var rest = previous.Data.bones[i].localScaled;
                deltas[i] = bones[i].localPosition - new Vector3(rest[0], rest[1], rest[2]);
            }
            for (int i = 0; i < blend.Length; i++) blend[i] = Loader.Renderer.GetBlendShapeWeight(i);
            hands.PrepareSkinChange();
            try
            {
                Apply(target, rotations, deltas, blend);
                CurrentId = id; SwitchCount++;
                Status = "F5 切换皮肤 · F11 切换渲染";
                Debug.Log("[MGFR skins] selected=" + id + " vertices=" + Loader.Renderer.sharedMesh.vertexCount + " switches=" + SwitchCount);
                return true;
            }
            catch (Exception error)
            {
                Apply(previous, rotations, deltas, blend);
                Status = "换肤失败，已恢复原皮肤";
                Debug.LogError("[MGFR skins] switch rolled back: " + error.GetType().Name + ": " + error.Message);
                return false;
            }
        }
        void Apply(SiAppearance target, Quaternion[] rotations, Vector3[] deltas, float[] blend)
        {
            Loader.ApplyAppearance(target);
            var bones = Loader.Renderer.bones;
            for (int i = 0; i < bones.Length; i++)
            { bones[i].localPosition += deltas[i]; bones[i].localRotation = rotations[i]; }
            idle.RebindSkinRestPose(Loader);
            physics.RebindSkinRestPose();
            Style.BindAppearance(target);
            for (int i = 0; i < blend.Length; i++) Loader.Renderer.SetBlendShapeWeight(i, blend[i]);
            hands.RebuildSkinSurface();
        }
        void OnGUI()
        {
            if (!IsReady || Array.IndexOf(Environment.GetCommandLineArgs(), "-mgfr-skin-review") >= 0) return;
            var previousFont = GUI.skin.font; if (font != null) GUI.skin.font = font;
            GUILayout.BeginArea(new Rect(18, Screen.height - 132, 360, 83), GUI.skin.box);
            GUILayout.Label("皮肤：" + (CurrentId == "original" ? "原服装" : "蓝白泳装 · 赤脚 v4"));
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("原服装")) TrySelect("original");
            if (GUILayout.Button("蓝白泳装")) TrySelect("swimsuit");
            GUILayout.EndHorizontal(); GUILayout.Label(Status); GUILayout.EndArea();
            GUI.skin.font = previousFont;
        }
        void OnDestroy()
        {
            // Staging hierarchies are children of this object. Loader resources are
            // explicitly owned here because the existing loader has no unload API.
            foreach (var staging in stagingLoaders)
            {
                if (staging == null || !staging.IsReady) continue;
                var seen = new HashSet<Texture>();
                foreach (var material in staging.Materials)
                {
                    var texture = material.GetTexture("_MainTex");
                    if (texture != null && seen.Add(texture)) Destroy(texture);
                    Destroy(material);
                }
                Destroy(staging.Renderer.sharedMesh);
            }
            if (font != null) Destroy(font);
        }
    }
}
