using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace MGFR.BareHands
{
    // Calibrate the shared joint stream, before mesh fitting, collisions and pinch detection.
    public sealed class HandAlignment : MonoBehaviour
    {
        [Serializable]
        public sealed class Adjustment
        {
            public Vector3 offsetMetres;
            public Vector3 viewDegrees;
            public float handScale = 1f;
        }

        [Serializable]
        public sealed class Profile
        {
            public Adjustment left = new Adjustment();
            public Adjustment right = new Adjustment();
        }

        public static HandAlignment Instance { get; private set; }
        public Profile Settings = new Profile();
        public bool ShowPanel;
        public bool Bypass { get; private set; }
        BareHandInteraction interaction;
        Transform head;
        Font font;
        int selected;
        string status = "默认无补偿。先对齐手腕，再调整手长。";
        string directory;
        Rect window;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (UnityEngine.SceneManagement.SceneManager.GetActiveScene().name != MGFR.Character.SiCharacterBootstrap.SceneName)
                return;
            new GameObject("Hand alignment calibration").AddComponent<HandAlignment>();
        }

        void Awake() { Instance = this; }
        IEnumerator Start()
        {
            while ((interaction = FindAnyObjectByType<BareHandInteraction>()) == null || !interaction.IsReady)
                yield return null;
            head = Camera.main.transform;
            directory = Path.Combine(Path.GetDirectoryName(Application.dataPath), "HandCalibration");
            var args = Environment.GetCommandLineArgs();
            int index = Array.IndexOf(args, "-mgfr-hand-calibration-dir");
            if (index >= 0) directory = args[index + 1];
            if (Directory.Exists(directory))
            {
                var files = Directory.GetFiles(directory, "calibration-*.json");
                Array.Sort(files, StringComparer.Ordinal);
                if (files.Length > 0)
                {
                    Settings = JsonUtility.FromJson<Profile>(File.ReadAllText(files[files.Length - 1]));
                    status = "已载入上次保存的校准。";
                }
            }
            font = Font.CreateDynamicFontFromOSFont("Microsoft YaHei", 16);
            window = new Rect(Mathf.Max(5, (Screen.width - 475) * .5f), 35, 475, 660);
            Debug.Log("[MGFR hand alignment] Ready. F10 panel, hold F11 for uncorrected input. Identity defaults; calibration applies to depth, collisions and pinch together.");
        }

        void Update()
        {
            Bypass = Input.GetKey(KeyCode.F11);
            if (interaction != null && Input.GetKeyDown(KeyCode.F10))
            {
                ShowPanel = !ShowPanel;
                if (ShowPanel) interaction.DebugHands = true;
            }
        }

        public static Pose MapPose(Pose raw, Vector3 rawWrist, Pose headPose, Adjustment adjustment)
        {
            var turn = headPose.rotation * Quaternion.Euler(adjustment.viewDegrees) * Quaternion.Inverse(headPose.rotation);
            var wrist = headPose.position + turn * (rawWrist - headPose.position) + headPose.rotation * adjustment.offsetMetres;
            return new Pose(wrist + turn * (raw.position - rawWrist) * adjustment.handScale, turn * raw.rotation);
        }

        public void Apply(int hand, HandFrame frame)
        {
            if (head == null || Bypass || !frame.Tracked) return;
            var adjustment = hand == 0 ? Settings.left : Settings.right;
            var headPose = new Pose(head.position, head.rotation);
            var wrist = frame.Joints[1].position;
            for (int i = 0; i < 26; i++)
            {
                if (!frame.Valid[i]) continue;
                frame.Joints[i] = MapPose(frame.Joints[i], wrist, headPose, adjustment);
                frame.Radius[i] *= adjustment.handScale;
            }
        }

        void Change(Action<Adjustment> action)
        {
            if (selected != 1) action(Settings.left);
            if (selected != 0) action(Settings.right);
            status = "修改即时生效；按住 F11 比较原始位置。";
        }

        void Row(string title, float value, string suffix, Action<float> change, float step)
        {
            GUILayout.BeginHorizontal();
            GUILayout.Label(title, GUILayout.Width(150));
            if (GUILayout.Button("−", GUILayout.Width(55))) change(-step);
            GUILayout.Label(value.ToString("+0.0;-0.0;0.0") + suffix, GUILayout.Width(110));
            if (GUILayout.Button("+", GUILayout.Width(55))) change(step);
            GUILayout.EndHorizontal();
        }

        void Panel(int id)
        {
            selected = GUILayout.Toolbar(selected, new[] { "左手", "右手", "双手一起" });
            var adjustment = selected == 1 ? Settings.right : Settings.left;
            GUILayout.Label("先保持张手，停稳后看 F8 橙色轮廓。正值：右 / 上 / 远离眼睛。\n每次移动 5 毫米；双手不同可分别调整。");
            Row("左右位置", adjustment.offsetMetres.x * 1000, " mm", d => Change(a => a.offsetMetres.x = Mathf.Clamp(a.offsetMetres.x + d, -.15f, .15f)), .005f);
            Row("上下位置", adjustment.offsetMetres.y * 1000, " mm", d => Change(a => a.offsetMetres.y = Mathf.Clamp(a.offsetMetres.y + d, -.15f, .15f)), .005f);
            Row("前后位置", adjustment.offsetMetres.z * 1000, " mm", d => Change(a => a.offsetMetres.z = Mathf.Clamp(a.offsetMetres.z + d, -.15f, .15f)), .005f);
            GUILayout.Space(8);
            Row("手长（手腕固定）", (adjustment.handScale - 1) * 100, " %", d => Change(a => a.handScale = Mathf.Clamp(a.handScale + d, .7f, 1.4f)), .01f);
            GUILayout.Label("若近处对齐、远处偏：再微调视线角度。每次 0.5 度。");
            Row("左右视线角", adjustment.viewDegrees.y, "°", d => Change(a => a.viewDegrees.y = Mathf.Clamp(a.viewDegrees.y + d, -15, 15)), .5f);
            Row("俯仰视线角", adjustment.viewDegrees.x, "°", d => Change(a => a.viewDegrees.x = Mathf.Clamp(a.viewDegrees.x + d, -15, 15)), .5f);
            Row("旋转视线角", adjustment.viewDegrees.z, "°", d => Change(a => a.viewDegrees.z = Mathf.Clamp(a.viewDegrees.z + d, -15, 15)), .5f);
            GUILayout.Space(10);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("本次恢复零补偿"))
                Change(a => { a.offsetMetres = Vector3.zero; a.viewDegrees = Vector3.zero; a.handScale = 1; });
            if (GUILayout.Button("保存为新校准")) Save();
            if (GUILayout.Button("完成 / 关闭")) { ShowPanel = false; interaction.DebugHands = false; }
            GUILayout.EndHorizontal();
            GUILayout.Label(status);
            GUILayout.Label("F10 打开/关闭 · 按住 F11 看原始输入\n先对齐手腕，再调尺寸；请在近、远两处都检查。\n这会同时调整遮挡、碰撞和抓取位置。手掌方形边缘属于轮廓近似。");
            GUI.DragWindow(new Rect(0, 0, 475, 24));
        }

        void Save()
        {
            Directory.CreateDirectory(directory);
            string path = Path.Combine(directory, "calibration-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fffffff") + ".json");
            using (var writer = new StreamWriter(new FileStream(path, FileMode.CreateNew)))
                writer.Write(JsonUtility.ToJson(Settings, true));
            status = "已保存；下次启动自动载入。";
            Debug.Log("[MGFR hand alignment] Saved " + path + " " + JsonUtility.ToJson(Settings));
        }

        void OnGUI()
        {
            if (interaction == null || !interaction.IsReady || font == null) return;
            var previous = GUI.skin.font;
            GUI.skin.font = font;
            if (ShowPanel) window = GUILayout.Window(102618, window, Panel, "手部位置校准（F10）");
            else GUI.Label(new Rect(Screen.width - 410, Screen.height - 30, 400, 25), "F10 手部校准 · 按住 F11 对比原始位置");
            GUI.skin.font = previous;
        }
        void OnDestroy() { if (Instance == this) Instance = null; }
    }
}
