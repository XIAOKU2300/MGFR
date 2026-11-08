using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;
using UnityEngine.XR.Management;

namespace MGFR.SmokeTest
{
    /// <summary>
    /// Copies one XR device's pose onto this transform, and reports whether that
    /// device is actually being tracked.
    ///
    /// Unity's XR pipeline renders stereo from the camera transform but does not
    /// move it, so something has to carry the head pose. This does that job
    /// directly rather than pulling in a TrackedPoseDriver and the Input System
    /// action assets that come with it. For a link test, fewer moving parts is
    /// the point.
    ///
    /// It also reads two buttons, because a pose proves the controller is being
    /// seen while a button proves the controller is actually talking to us.
    /// </summary>
    [DisallowMultipleComponent]
    [DefaultExecutionOrder(-1000)]
    public sealed class XrDeviceFollower : MonoBehaviour
    {
        /// <summary>The switch that keeps a run off XR entirely, for a desktop-only session.</summary>
        public const string NoXrFlag = "-mgfr-noxr";

        /// <summary>
        /// When true the follower never asks the XR input system for anything.
        ///
        /// Asking is not passive. <c>InputDevices.GetDeviceAtXRNode</c> is what
        /// brings Unity's XR up in the first place, so a desktop-only run has to
        /// stop asking rather than merely stop rendering. Set by
        /// <see cref="NoXrFlag"/> and left alone otherwise.
        /// </summary>
        public static bool Suppressed { get; set; }

        /// <summary>
        /// Reads <see cref="NoXrFlag"/> before the first scene loads and, when it is
        /// present, shuts XR down and keeps it down.
        ///
        /// This has to be a runtime initialiser rather than a MonoBehaviour: Unity
        /// starts the XR loader during engine startup, before any scene exists, so
        /// there is no object to hang it on. Stopping the subsystems is not enough
        /// on its own either - the next InputDevices query would start them again -
        /// which is why <see cref="Suppressed"/> is set as well.
        /// </summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void ApplyNoXrSwitch()
        {
            bool requested = false;
            foreach (string arg in Environment.GetCommandLineArgs())
            {
                if (string.Equals(arg, NoXrFlag, StringComparison.Ordinal))
                {
                    requested = true;
                    break;
                }
            }

            if (!requested)
                return;

            Suppressed = true;

            try
            {
                XRSettings.enabled = false;

                XRGeneralSettings settings = XRGeneralSettings.Instance;
                if (settings != null && settings.Manager != null)
                {
                    settings.Manager.StopSubsystems();
                    settings.Manager.DeinitializeLoader();
                }

                Debug.Log($"[MGFR] {NoXrFlag}: XR stopped and suppressed, this run is desktop only.");
            }
            catch (Exception e)
            {
                // Never fatal. The switch exists to make a desktop run predictable,
                // so failing to stop XR must not be what stops the run.
                Debug.LogWarning($"[MGFR] {NoXrFlag}: could not stop XR " +
                                 $"({e.GetType().Name}: {e.Message}); the follower is suppressed regardless.");
            }
        }

        [Tooltip("Which XR device drives this transform.")]
        public XRNode node = XRNode.Head;

        /// <summary>The device exists and is reporting a pose this frame.</summary>
        public bool IsTracked { get; private set; }

        /// <summary>
        /// True once the device has reported a real, tracked pose.
        ///
        /// Deliberately not the same thing as <see cref="IsTracked"/>, which is per
        /// frame. This is "a headset has been seen at some point during this run",
        /// which is what the desktop preview needs to know before it hands the
        /// camera over.
        /// </summary>
        public bool HasTrackedPose { get; private set; }

        /// <summary>True only on the frame a button went from up to down.</summary>
        public bool ButtonPressedThisFrame { get; private set; }

        /// <summary>Which button went down this frame, or empty.</summary>
        public string PressedButton { get; private set; } = "";

        public string PoseSource { get; private set; } = "waiting";
        public Vector3 LastLocalPosition { get; private set; }
        readonly List<XRNodeState> _nodeStates = new List<XRNodeState>(8);
        float _nextPoseLog;
        bool _loggedWaiting;
        InputDevice _device;
        bool _hadDevice;
        bool _buttonWasDown;

        void OnEnable() => Application.onBeforeRender += BeforeRender;
        void OnDisable() => Application.onBeforeRender -= BeforeRender;
        [BeforeRenderOrder(-20000)]
        void BeforeRender()
        {
            // Match tracked-pose drivers: use the freshest head pose before submit.
            if (node != XRNode.Head || Suppressed || !_device.isValid) return;
            // The render deadline only samples the cached device. Device discovery,
            // fallback enumeration, buttons and logging stay in Update.
            if (_device.TryGetFeatureValue(CommonUsages.isTracked,out bool tracked)&&tracked&&
                _device.TryGetFeatureValue(CommonUsages.devicePosition,out Vector3 p)&&
                _device.TryGetFeatureValue(CommonUsages.deviceRotation,out Quaternion q))
                ApplyTrackedPose(p,q);
        }
        void Update() => UpdatePose();
        void UpdatePose()
        {
            if (Suppressed)
            {
                if (_hadDevice)
                {
                    _hadDevice = false;
                    Debug.Log($"[MGFR] {node} follower suppressed.");
                }

                IsTracked = false;
                ButtonPressedThisFrame = false;
                PressedButton = "";
                return;
            }

            _device = InputDevices.GetDeviceAtXRNode(node);

            if (!_device.isValid)
            {
                if (_hadDevice)
                {
                    _hadDevice = false;
                    Debug.Log($"[MGFR] {node} device disappeared.");
                }

                IsTracked = false;
                ButtonPressedThisFrame = false;
                PressedButton = "";
                return;
            }

            if (!_hadDevice)
            {
                _hadDevice = true;
                Debug.Log($"[MGFR] {node} device appeared: {Describe(_device)}");
            }

            bool hasTracked = _device.TryGetFeatureValue(CommonUsages.isTracked, out bool tracked);
            // OpenXR head devices expose devicePosition/deviceRotation. Some
            // runtimes also expose centerEye*. Prefer a complete native pair.
            bool gotPosition = _device.TryGetFeatureValue(CommonUsages.devicePosition, out Vector3 position);
            bool gotRotation = _device.TryGetFeatureValue(CommonUsages.deviceRotation, out Quaternion rotation);
            string source = "device pose";
            if (node == XRNode.Head && (!gotPosition || !gotRotation))
            {
                gotPosition = _device.TryGetFeatureValue(CommonUsages.centerEyePosition, out position);
                gotRotation = _device.TryGetFeatureValue(CommonUsages.centerEyeRotation, out rotation);
                source = "center eye features";
            }
            if (node == XRNode.Head && (!gotPosition || !gotRotation || !hasTracked))
            {
                InputTracking.GetNodeStates(_nodeStates);
                foreach (var state in _nodeStates)
                {
                    if (state.nodeType != XRNode.CenterEye && state.nodeType != XRNode.Head) continue;
                    if (!state.tracked || !state.TryGetPosition(out var p) || !state.TryGetRotation(out var q)) continue;
                    position = p; rotation = q;
                    gotPosition = gotRotation = tracked = hasTracked = true;
                    source = "tracked XR node " + state.nodeType;
                    break;
                }
            }
            IsTracked = hasTracked && tracked && gotPosition && gotRotation;
            if (IsTracked)
            {
                ApplyTrackedPose(position, rotation);
                PoseSource = source;
                if (node == XRNode.Head && Time.unscaledTime >= _nextPoseLog)
                {
                    _nextPoseLog = Time.unscaledTime + 2f;
                    Debug.Log($"[MGFR VR fix] head source={source} local={position:F3} rotation={rotation.eulerAngles:F1}");
                }
            }
            else if (node == XRNode.Head && !_loggedWaiting)
            {
                _loggedWaiting = true;
                Debug.LogWarning($"[MGFR VR fix] waiting for 6DoF head pose: tracked={tracked}, position={gotPosition}, rotation={gotRotation}");
            }

            ReadButtons();
        }

        /// <summary>The single pose application path, also used by the room-motion regression check.</summary>
        public bool ApplyTrackedPose(Vector3 position, Quaternion rotation)
        {
            if (!Finite(position.x) || !Finite(position.y) || !Finite(position.z) ||
                !Finite(rotation.x) || !Finite(rotation.y) || !Finite(rotation.z) || !Finite(rotation.w) ||
                Quaternion.Dot(rotation, rotation) < 0.000001f) return false;
            HasTrackedPose = true;
            LastLocalPosition = position;
            transform.SetLocalPositionAndRotation(position, rotation.normalized);
            return true;
        }
        static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);

        void ReadButtons()
        {
            _device.TryGetFeatureValue(CommonUsages.triggerButton, out bool trigger);
            _device.TryGetFeatureValue(CommonUsages.primaryButton, out bool primary);

            string down = trigger ? "trigger" : primary ? "primary" : "";
            bool isDown = down.Length > 0;

            ButtonPressedThisFrame = isDown && !_buttonWasDown;
            PressedButton = ButtonPressedThisFrame ? down : "";
            _buttonWasDown = isDown;
        }

        static string Describe(InputDevice device)
        {
            // serialNumber is a property on InputDevice, not a CommonUsages
            // feature: CommonUsages holds no serial-number or device-name usage,
            // and both are already available directly on the device.
            string manufacturer = string.IsNullOrEmpty(device.manufacturer) ? "?" : device.manufacturer;
            string name = string.IsNullOrEmpty(device.name) ? "?" : device.name;
            string serial = string.IsNullOrEmpty(device.serialNumber) ? "?" : device.serialNumber;
            return $"{manufacturer} {name} (serial {serial})";
        }
    }
}
