using MGFR.BareHands;
using MGFR.SmokeTest;
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
        public string ModeLabel => Mode == ControllerInteractionMode.Auto ? "自动" : Mode == ControllerInteractionMode.Controller ? "手柄" : "裸手";
        public bool Driving { get; private set; }
        BareHandInteraction hands;
        readonly bool[] armed = new bool[2];
        readonly bool[] closed = new bool[2];
        bool previousDriving;
        void Awake() { Instance = this; }
        public void CycleMode() { Mode = (ControllerInteractionMode)(((int)Mode + 1) % 3); }
        void LateUpdate()
        {
            if (Manual || XrDeviceFollower.Suppressed) return;
            if (hands == null) hands = FindAnyObjectByType<BareHandInteraction>();
            if (hands == null || !hands.IsReady) return;
            var left = InputDevices.GetDeviceAtXRNode(XRNode.LeftHand);
            var right = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
            bool physical = TrackedController(left) || TrackedController(right);
            Driving = Mode == ControllerInteractionMode.Controller || (Mode == ControllerInteractionMode.Auto && physical);
            if (Driving != previousDriving)
            {
                hands.CancelForWardrobe(0); hands.CancelForWardrobe(1);
                hands.Source.Frames[0].Clear(); hands.Source.Frames[1].Clear();
                hands.Source.RenderFrames[0].Clear(); hands.Source.RenderFrames[1].Clear();
                for (int h = 0; h < 2; h++) { armed[h] = closed[h] = false; }
                previousDriving = Driving;
            }
            hands.Source.ControllerDriven = Driving;
            if (!Driving) return;
            hands.PreferBareHands = true; // Share the same cloth/wardrobe ownership pipeline.
            Sample(0, left); Sample(1, right);
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
            if (hands != null && hands.Source != null) hands.Source.ControllerDriven = false;
            if (Instance == this) Instance = null;
        }
    }
}
