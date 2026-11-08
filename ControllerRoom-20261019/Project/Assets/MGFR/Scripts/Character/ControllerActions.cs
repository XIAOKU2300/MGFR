using System;
using MGFR.BareHands;
using MGFR.Dialogue;
using MGFR.Experience;
using MGFR.Skins;
using MGFR.Wardrobe;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.XR;

namespace MGFR.Character
{
    public struct ControllerButtons
    {
        public bool LeftTracked, RightTracked, X, Y, A, B;
        public Vector2 LeftStick, RightStick;
    }

    public sealed class ControllerEdges
    {
        bool armed, primary, secondary;
        public void Read(bool tracked, bool a, bool b, out bool pressedA, out bool pressedB)
        {
            pressedA = pressedB = false;
            if (!tracked) { armed = primary = secondary = false; return; }
            if (!armed) { if (!a && !b) armed = true; primary = a; secondary = b; return; }
            pressedA = a && !primary; pressedB = b && !secondary;
            primary = a; secondary = b;
        }
    }

    [DefaultExecutionOrder(-400)]
    public sealed class ControllerActions : MonoBehaviour
    {
        public static ControllerActions Instance { get; private set; }
        public bool MenuOpen { get; private set; }
        public bool Placing { get; private set; }
        public int Selected { get; private set; }
        public string Feedback { get; private set; } = "Y 打开快捷菜单";
        public bool Manual;
        public const int ItemCount = 12;
        public ControllerMenuView View { get; private set; }
        public SiCharacterController Character { get; private set; }
        readonly ControllerEdges leftEdges = new ControllerEdges(), rightEdges = new ControllerEdges();
        RoomFloorPlacement floor;
        SiSkinSwitcher skins;
        AutomaticVoiceSession voice;
        CameraChatOverlay captions;
        IdleMotionPlayer idle;
        WardrobeLiveRuntime wardrobe;
        BareHandInteraction hands;
        Vector3 savedPosition;
        float savedYaw, savedScale, savedGround, navWait, feedbackUntil;
        bool neutralRequired, navHeld; int savedRevision;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (SceneManager.GetActiveScene().name != SiCharacterBootstrap.SceneName) return;
            var go = new GameObject("Controller room controls");
            go.AddComponent<ControllerActions>();
            go.AddComponent<ControllerGripSource>();
        }
        void Awake() { Instance = this; }
        void Start()
        {
            Character = FindAnyObjectByType<SiCharacterController>();
            floor = FindAnyObjectByType<RoomFloorPlacement>();
            skins = FindAnyObjectByType<SiSkinSwitcher>();
            voice = FindAnyObjectByType<AutomaticVoiceSession>();
            captions = FindAnyObjectByType<CameraChatOverlay>();
            idle = FindAnyObjectByType<IdleMotionPlayer>();
            wardrobe = FindAnyObjectByType<WardrobeLiveRuntime>();
            hands = FindAnyObjectByType<BareHandInteraction>();
            View = gameObject.AddComponent<ControllerMenuView>();
        }
        void Update()
        {
            if (Manual || XrDeviceFollowerSuppressed()) return;
            Step(ReadDevices(), Time.unscaledDeltaTime);
        }
        static bool XrDeviceFollowerSuppressed() => MGFR.SmokeTest.XrDeviceFollower.Suppressed;

        public static ControllerButtons ReadDevices()
        {
            var result = new ControllerButtons();
            var left = InputDevices.GetDeviceAtXRNode(XRNode.LeftHand);
            var right = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
            result.LeftTracked = left.isValid && left.TryGetFeatureValue(CommonUsages.isTracked, out bool lt) && lt;
            result.RightTracked = right.isValid && right.TryGetFeatureValue(CommonUsages.isTracked, out bool rt) && rt;
            if (result.LeftTracked)
            {
                left.TryGetFeatureValue(CommonUsages.primaryButton, out result.X);
                left.TryGetFeatureValue(CommonUsages.secondaryButton, out result.Y);
                left.TryGetFeatureValue(CommonUsages.primary2DAxis, out result.LeftStick);
            }
            if (result.RightTracked)
            {
                right.TryGetFeatureValue(CommonUsages.primaryButton, out result.A);
                right.TryGetFeatureValue(CommonUsages.secondaryButton, out result.B);
                right.TryGetFeatureValue(CommonUsages.primary2DAxis, out result.RightStick);
            }
            return result;
        }

        public void Step(ControllerButtons frame, float seconds)
        {
            float dt = Mathf.Clamp(seconds, 0, .05f);
            leftEdges.Read(frame.LeftTracked, frame.X, frame.Y, out _, out bool menu);
            rightEdges.Read(frame.RightTracked, frame.A, frame.B, out bool confirm, out bool back);
            if (menu) { MenuOpen = !MenuOpen; neutralRequired = true; navHeld = false; }
            if (floor != null) floor.ControllerShortcutBlocked = MenuOpen || Placing;
            if (Placing && floor != null && floor.AnchorRevision != savedRevision)
            { Placing = MenuOpen = false; Say("地面已重新标定，已更新摆放位置"); return; }
            if (back)
            {
                if (MenuOpen) MenuOpen = false;
                else if (Placing) CancelPlacement();
                return;
            }
            if (MenuOpen)
            {
                navWait = Mathf.Max(0, navWait - dt);
                float axis = frame.RightTracked && float.IsFinite(frame.RightStick.y) ? frame.RightStick.y : 0;
                if (Mathf.Abs(axis) < .25f) navHeld = false;
                if (Mathf.Abs(axis) > .65f && (!navHeld || navWait <= 0))
                {
                    Selected = (Selected + (axis < 0 ? 1 : ItemCount - 1)) % ItemCount;
                    navWait = navHeld ? .22f : .42f; navHeld = true;
                }
                if (confirm) Activate(Selected);
                return;
            }
            if (!Placing || Character == null) return;
            if (confirm) { Character.RememberRoomPlacement(); Placing = false; Say("已保存摆放位置"); return; }
            if (!frame.LeftTracked || !frame.RightTracked) { neutralRequired = true; return; }
            if (neutralRequired)
            {
                if (frame.LeftStick.sqrMagnitude < .04f && frame.RightStick.sqrMagnitude < .04f) neutralRequired = false;
                return;
            }
            if (HoldingAnything()) { Say("请先松开手中的物品"); return; }
            var camera = Camera.main;
            var forward = Vector3.ProjectOnPlane(camera != null ? camera.transform.forward : Vector3.forward, Vector3.up);
            if (forward.sqrMagnitude < .01f) forward = Vector3.forward;
            forward.Normalize();
            var rightDirection = Vector3.Cross(Vector3.up, forward);
            var move = new Vector2(Deadzone(frame.LeftStick.x), Deadzone(frame.LeftStick.y));
            move = Vector2.ClampMagnitude(move, 1f);
            float x = Deadzone(frame.RightStick.x), y = Deadzone(frame.RightStick.y);
            Character.AdjustRoomPlacement((rightDirection * move.x + forward * move.y) * (.35f * dt),
                x * 60f * dt, frame.X ? 0 : y * .25f * dt, frame.X ? y * .06f * dt : 0);
        }
        public static float Deadzone(float value)
        { return !float.IsFinite(value) || Mathf.Abs(value) <= .22f ? 0 : Mathf.Sign(value) * Mathf.Clamp01((Mathf.Abs(value) - .22f) / .78f); }
        bool HoldingAnything()
        {
            if (wardrobe != null && (wardrobe.OwnsHand(0) || wardrobe.OwnsHand(1))) return true;
            return hands != null && (hands.GrabbedBody[0] >= 0 || hands.GrabbedBody[1] >= 0);
        }
        void Say(string value) { Feedback = value; feedbackUntil = Time.unscaledTime + 3f; }

        public void Activate(int item)
        {
            if (Character == null) { Say("角色还在加载"); return; }
            if ((item == 0 || item == 1 || item == 2 || item == 8) && HoldingAnything())
            { Say("请先松开手中的物品"); return; }
            switch (item)
            {
                case 0:
                    if (!Placing)
                    {
                        savedPosition = Character.PlanarPosition; savedYaw = Character.Yaw;
                        savedScale = Character.CharacterScale; savedGround = Character.GroundHeight;
                        Placing = true; savedRevision = floor != null ? floor.AnchorRevision : 0;
                    }
                    MenuOpen = false; neutralRequired = true; Say("先让摇杆回中，再调整角色"); break;
                case 1:
                    if (Placing) { Character.RememberRoomPlacement(); Placing = false; }
                    floor?.RequestPlacement(); MenuOpen = false; Say("正在按地面重新放到面前"); break;
                case 2:
                    if (skins != null && skins.IsReady) Say(skins.TrySelect(skins.CurrentId == "original" ? "swimsuit" : "original") ? "已切换皮肤" : "切换失败，请稍后再试");
                    else Say("皮肤还在加载"); break;
                case 3:
                    if (voice != null) { voice.SetMuted(!voice.Muted); Say(voice.Muted ? "麦克风已静音" : "麦克风已开启"); }
                    else Say("语音尚未就绪"); break;
                case 4:
                    if (captions != null) { captions.SetVisible(!captions.Visible); Say(captions.Visible ? "字幕已显示" : "字幕已隐藏"); } break;
                case 5:
                    if (idle != null) { idle.NaturalIdle = !idle.NaturalIdle; Say(idle.NaturalIdle ? "自然待机已开启" : "已切换原待机"); } break;
                case 6:
                    if (wardrobe != null) { wardrobe.SetInteractionEnabled(!wardrobe.Enabled); Say(wardrobe.Enabled ? "衣物穿脱已开启" : "衣物穿脱已关闭"); } break;
                case 7:
                    wardrobe?.ResetAll(); Say("已恢复全部衣物和鞋子"); break;
                case 8:
                    ControllerGripSource.Instance?.CycleMode(); Say("已切换交互方式"); break;
                case 9:
                    FindAnyObjectByType<ControllerHands>()?.ResetBall(); Say("小球已放回角色身边"); break;
                case 10: Character.TriggerBlink(); Character.ToggleBlush(); Say("已切换害羞表情"); break;
                case 11: MenuOpen = false; break;
            }
        }
        void CancelPlacement()
        {
            Character.RestoreRoomPlacement(savedPosition, savedYaw, savedScale, savedGround);
            Placing = false; Say("已取消本次调整");
        }
        public string ItemLabel(int item)
        {
            switch (item)
            {
                case 0: return "调整角色位置";
                case 1: return "重新放到面前";
                case 2: return "切换皮肤";
                case 3: return voice != null && voice.Muted ? "麦克风：静音" : "麦克风：开启";
                case 4: return captions != null && captions.Visible ? "字幕：显示" : "字幕：隐藏";
                case 5: return idle != null && idle.NaturalIdle ? "待机：自然" : "待机：原动作";
                case 6: return wardrobe == null || wardrobe.Enabled ? "衣物穿脱：开启" : "衣物穿脱：关闭";
                case 7: return "恢复全部衣物和鞋子";
                case 8: return "交互：" + (ControllerGripSource.Instance != null ? ControllerGripSource.Instance.ModeLabel : "自动");
                case 9: return "找回小球";
                case 10: return "切换害羞表情";
                default: return "关闭菜单";
            }
        }
        void LateUpdate()
        {
            if (View == null) return;
            if (MenuOpen)
            {
                int first = Selected / 5 * 5;
                var rows = new string[Mathf.Min(5, ItemCount - first)];
                for (int i = 0; i < rows.Length; i++) rows[i] = (first + i == Selected ? "▶  " : "    ") + ItemLabel(first + i);
                View.Show("角色与互动", rows, "右摇杆选择   A 确认   B / Y 关闭", Feedback);
            }
            else if (Placing)
                View.Show("摆放角色", new[] { "左摇杆：前后左右移动", "右摇杆：左右转向 / 上下缩放", "按住 X + 右摇杆：微调高度", "A 保存   B 取消并还原" }, "手柄追踪恢复后，请先让摇杆回中", Feedback);
            else if (Time.unscaledTime < 12f || Time.unscaledTime < feedbackUntil)
                View.Show("手柄操作", new[] { "Y 快捷菜单", "长按左摇杆：重新放到面前", "扳机 / 握键：抓取与松开" }, "先松开抓取键，再靠近物品按下", Feedback);
            else View.Hide();
        }
        void OnDestroy() { if (Instance == this) Instance = null; }
    }
}
