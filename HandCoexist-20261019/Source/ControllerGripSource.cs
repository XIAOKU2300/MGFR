using MGFR.BareHands;
using MGFR.SmokeTest;
using MGFR.Wardrobe;
using UnityEngine;
using UnityEngine.XR;

namespace MGFR.Character
{
    public enum ControllerInteractionMode { Auto, Controller, BareHands }

    [DefaultExecutionOrder(1200)]
    public sealed class ControllerGripSource : MonoBehaviour
    {
        public static ControllerGripSource Instance { get; private set; }
        public ControllerInteractionMode Mode = ControllerInteractionMode.Auto;
        public bool Manual;
        public string ModeLabel => Mode == ControllerInteractionMode.Auto ? "自动（裸手优先）" : Mode == ControllerInteractionMode.Controller ? "手柄" : "裸手";
        public bool Driving => hands != null && hands.Source != null && hands.Source.ControllerDriven;
        BareHandInteraction hands;
        readonly bool[] armed = new bool[2], closed = new bool[2];
        void Awake() { Instance = this; }
        public void CycleMode() { Mode = (ControllerInteractionMode)(((int)Mode + 1) % 3); }
        void LateUpdate()
        {
            if (Manual || XrDeviceFollower.Suppressed) return;
            if (hands == null) hands = FindAnyObjectByType<BareHandInteraction>();
            if (hands == null || !hands.IsReady) return;
            var left = InputDevices.GetDeviceAtXRNode(XRNode.LeftHand);
            var right = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
            UpdateRouting(TrackedController(left), TrackedController(right));
            if (hands.Source.IsControllerPose(0)) Sample(0, left);
            if (hands.Source.IsControllerPose(1)) Sample(1, right);
        }

        public void UpdateRouting(bool leftController, bool rightController)
        {
            if (hands == null) hands = FindAnyObjectByType<BareHandInteraction>();
            if (hands == null || !hands.IsReady) return;
            var wardrobe = WardrobeLiveRuntime.Instance;
            for (int h = 0; h < 2; h++)
            {
                bool available = h == 0 ? leftController : rightController;
                bool holding = (wardrobe != null && wardrobe.OwnsHand(h)) || hands.GrabbedBody[h] >= 0;
                bool wanted = WantsController(Mode, available, hands.Source.HasFreshNativePose(h), hands.Source.IsControllerPose(h), holding);
                if (wanted != hands.Source.IsControllerPose(h))
                {
                    hands.CancelForWardrobe(h);
                    wardrobe?.CancelInputHand(h);
                    armed[h] = closed[h] = false;
                    hands.Source.UseControllerPose(h, wanted);
                }
            }
            hands.PreferBareHands = true; // The common interaction pipeline accepts either source per hand.
        }

        public static bool WantsController(ControllerInteractionMode mode, bool controller, bool native, bool wasController, bool holding)
        {
            if (mode == ControllerInteractionMode.BareHands) return false;
            if (mode == ControllerInteractionMode.Controller) return true;
            // Keep an existing grab attached until release, but continue native
            // tracking and real-hand occlusion even during that controller grab.
            return controller && (!native || (wasController && holding));
        }
        static bool TrackedController(InputDevice device)
        {
            return device.isValid && (device.characteristics & InputDeviceCharacteristics.Controller) != 0 &&
                (device.characteristics & InputDeviceCharacteristics.HandTracking) == 0 &&
                device.TryGetFeatureValue(CommonUsages.isTracked, out bool tracked) && tracked;
        }
        void Sample(int h, InputDevice device)
        {
            Vector3 position = Vector3.zero; Quaternion rotation = Quaternion.identity;
            bool tracked = TrackedController(device) &&
                device.TryGetFeatureValue(CommonUsages.devicePosition, out position) &&
                device.TryGetFeatureValue(CommonUsages.deviceRotation, out rotation);
            if (!tracked)
            { armed[h] = closed[h] = false; hands.Source.PublishControllerFrame(h, null, false); return; }
            device.TryGetFeatureValue(CommonUsages.grip, out float grip);
            device.TryGetFeatureValue(CommonUsages.trigger, out float trigger);
            var origin = Camera.main != null ? Camera.main.transform.parent : null;
            var pose = new Pose(origin != null ? origin.TransformPoint(position) : position,
                origin != null ? origin.rotation * rotation : rotation);
            bool suppress = ControllerActions.Instance != null && ControllerActions.Instance.Placing;
            bool pinch = UpdateGrip(h, Mathf.Max(grip, trigger), suppress);
            hands.Source.PublishControllerFrame(h, MakeFrame(pose, h, pinch), true);
        }
        public bool UpdateGrip(int h, float pressure, bool suppress)
        {
            if (!float.IsFinite(pressure) || suppress) { armed[h] = closed[h] = false; return false; }
            if (pressure < .25f) { armed[h] = true; closed[h] = false; }
            if (!armed[h]) return false;
            if (pressure >= .65f) closed[h] = true;
            else if (pressure <= .35f) closed[h] = false;
            return closed[h];
        }
        public static readonly Vector3 PinchOffset = new Vector3(0, -.015f, .075f);
        public static Pose[] MakeFrame(Pose controller, int hand, bool pinch)
        {
            var result = new Pose[26]; float sign = hand == 0 ? -1f : 1f;
            Vector3 point = controller.position + controller.rotation * PinchOffset;
            for (int i = 0; i < result.Length; i++) result[i] = new Pose(point, controller.rotation);
            void Put(int i, Vector3 local) { result[i] = new Pose(point + controller.rotation * local, controller.rotation); }
            Put(0, new Vector3(0, -.015f, -.045f)); Put(1, new Vector3(0, -.018f, -.09f));
            for (int finger = 0; finger < 5; finger++)
            {
                int start = finger == 0 ? 2 : 6 + (finger - 1) * 5;
                int count = finger == 0 ? 4 : 5;
                for (int j = 0; j < count; j++)
                    Put(start + j, new Vector3(sign * (finger - 2) * .017f, -.008f, -.065f + j * .018f));
            }
            Put(12, new Vector3(0, -.018f, -.01f));
            Put(5, new Vector3(-sign * (pinch ? .009f : .045f), 0, 0));
            Put(10, new Vector3(sign * (pinch ? .009f : .045f), 0, 0));
            return result;
        }
        void OnDestroy()
        {
            if (hands != null && hands.Source != null)
                for (int h = 0; h < 2; h++) hands.Source.UseControllerPose(h, false);
            if (Instance == this) Instance = null;
        }
    }
}
