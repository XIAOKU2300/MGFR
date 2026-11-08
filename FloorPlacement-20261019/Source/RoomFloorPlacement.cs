using System.Collections.Generic;
using MGFR.SmokeTest;
using UnityEngine;
using UnityEngine.XR;

namespace MGFR.Character
{
    // Wait for the requested reference space and a fresh tracked pose. The
    // fallback is deliberately labelled estimated and can later upgrade to floor.
    public sealed class FloorPlacementGate
    {
        public bool Placed { get; private set; }
        public bool Measured { get; private set; }
        float began = -1f, stableSince = -1f;
        bool previousFloor, pending;

        public void RequestPlacement() { pending = true; stableSince = -1f; }

        public bool Observe(float now, bool floor, bool tracked, bool originUpdated)
        {
            if (began < 0f) began = now;
            if (originUpdated || floor != previousFloor)
            { stableSince = -1f; pending = true; }
            previousFloor = floor;
            if (!tracked) { stableSince = -1f; return false; }
            if (stableSince < 0f) stableSince = now;
            if (now - stableSince < .35f) return false;
            if (floor && (!Placed || !Measured || pending))
            { Placed = Measured = true; pending = false; return true; }
            if (!floor && now - began >= 8f && (!Placed || pending))
            { Placed = true; Measured = false; pending = false; return true; }
            return false;
        }
    }

    [DisallowMultipleComponent]
    public sealed class RoomFloorPlacement : MonoBehaviour
    {
        public float Distance = 1.5f;
        public bool RoomReady => gate.Placed;
        public bool HasCalibratedFloor => gate.Measured;
        public string Status { get; private set; } = "等待地面与头显定位";
        readonly FloorPlacementGate gate = new FloorPlacementGate();
        readonly List<XRInputSubsystem> inputs = new List<XRInputSubsystem>(2);
        XRInputSubsystem input;
        Transform rig;
        Camera view;
        XrDeviceFollower follower;
        SiCharacterController character;
        float nextDiscovery, nextRequest, stickHeldSince = -1f;
        bool originUpdated, stickConsumed;

        public void Bind(Transform trackingRig, Camera camera, XrDeviceFollower head, SiCharacterController target)
        { rig = trackingRig; view = camera; follower = head; character = target; }

        public bool Tick()
        {
            if (rig == null || follower == null || character == null || XrDeviceFollower.Suppressed)
                return RoomReady;
            float now = Time.unscaledTime;
            if ((input == null || !input.running) && now >= nextDiscovery)
            {
                nextDiscovery = now + .5f;
                SetSubsystem(null);
                SubsystemManager.GetSubsystems(inputs);
                foreach (var candidate in inputs)
                    if (candidate.running) { SetSubsystem(candidate); break; }
            }
            bool floor = input != null && input.running &&
                (input.GetTrackingOriginMode() & TrackingOriginModeFlags.Floor) != 0;
            if (!floor && input != null && input.running && now >= nextRequest)
            {
                nextRequest = now + 1f;
                if ((input.GetSupportedTrackingOriginModes() & TrackingOriginModeFlags.Floor) != 0)
                    input.TrySetTrackingOriginMode(TrackingOriginModeFlags.Floor);
                // Re-query on subsequent frames; never treat a request as success.
            }
            ReadRepositionInput(now);
            bool changed = originUpdated;
            originUpdated = false;
            if (gate.Observe(now, floor, follower.IsTracked, changed))
                ApplyAnchor(gate.Measured);
            return RoomReady;
        }

        void SetSubsystem(XRInputSubsystem value)
        {
            if (input == value) return;
            if (input != null) input.trackingOriginUpdated -= OnOriginUpdated;
            input = value;
            if (input != null) input.trackingOriginUpdated += OnOriginUpdated;
            gate.RequestPlacement();
        }

        void OnOriginUpdated(XRInputSubsystem _) { originUpdated = true; }

        void ReadRepositionInput(float now)
        {
            if (Input.GetKeyDown(KeyCode.End)) RequestPlacement();
            var left = InputDevices.GetDeviceAtXRNode(XRNode.LeftHand);
            bool held = left.isValid && left.TryGetFeatureValue(CommonUsages.isTracked, out bool tracked) && tracked &&
                left.TryGetFeatureValue(CommonUsages.primary2DAxisClick, out bool clicked) && clicked;
            if (!held) { stickHeldSince = -1f; stickConsumed = false; return; }
            if (stickHeldSince < 0f) stickHeldSince = now;
            if (!stickConsumed && now - stickHeldSince >= .8f)
            { stickConsumed = true; RequestPlacement(); }
        }

        public void RequestPlacement()
        {
            gate.RequestPlacement();
            Status = "正在按地面重新放置";
        }

        void ApplyAnchor(bool measured)
        {
            // Tracking poses are relative to the reference-space floor. Head
            // height must never be subtracted in this mode (including crouching).
            float height = measured ? 0f : 1.6f - follower.LastLocalPosition.y;
            rig.SetPositionAndRotation(new Vector3(0f, height, 0f), Quaternion.identity);
            var headPosition = rig.TransformPoint(follower.LastLocalPosition);
            var forward = rig.TransformDirection(view.transform.localRotation * Vector3.forward);
            float ground = measured ? rig.TransformPoint(Vector3.zero).y : 0f;
            character.PlaceOnGround(headPosition, forward, Distance, ground);
            Status = measured ? "已按标定地面放置" : "未收到标定地面，暂用估计高度";
            Debug.Log($"[MGFR floor] measured={measured}, anchor={character.transform.position:F3}, distance={Distance:F2}; End or hold left stick 0.8s to reposition");
        }

        // Existing diagnostic callers may explicitly enter room mode without XR.
        public void EnterFromCurrentPose()
        {
            if (RoomReady || follower == null || !follower.HasTrackedPose) return;
            bool floor = input != null && input.running &&
                (input.GetTrackingOriginMode() & TrackingOriginModeFlags.Floor) != 0;
            gate.Observe(0f, floor, true, false);
            gate.Observe(9f, floor, true, false);
            ApplyAnchor(floor);
        }

        void OnDestroy() { if (input != null) input.trackingOriginUpdated -= OnOriginUpdated; }
    }
}
