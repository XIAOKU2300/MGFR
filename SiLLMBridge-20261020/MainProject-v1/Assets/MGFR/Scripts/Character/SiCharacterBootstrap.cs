using System.Collections.Generic;
using MGFR.Dialogue;
using MGFR.SmokeTest;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.XR;

namespace MGFR.Character
{
    /// <summary>
    /// Builds the character scene in code, the same way the smoke rig builds its
    /// own. The saved scene stays empty apart from this component, which means
    /// there is exactly one place where the scene is defined and no chance of a
    /// half-edited scene drifting away from the code.
    ///
    /// The green background is the chroma key. It is not decoration: ALVR's
    /// RgbChromaKey composites the real room over pixels close to RGB(0,255,0), so
    /// anything that covers the frame - a ground plane, a skybox, a fog - would
    /// punch a hole in the passthrough. That is why there is no floor here, and why
    /// the ground reference is an optional wireframe grid rather than a plane.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SiCharacterBootstrap : MonoBehaviour
    {
        public const string SceneName = "SiCharacter";

        /// <summary>ALVR's key colour, matching SmokeTestRig.</summary>
        static readonly Color KeyGreen = new Color(0f, 1f, 0f, 1f);

        [Header("Preview camera")]
        [Tooltip("Where the camera sits when no headset is attached, in metres from the character.")]
        public float orbitDistance = 2.2f;
        public float orbitSensitivity = 0.25f;
        public float zoomSensitivity = 0.6f;

        [Header("Ground reference")]
        [Tooltip("Off by default: a visible grid in the headset would sit in the middle of the real room.")]
        public bool showGroundGrid;

        Transform _cameraRig;
        Camera _camera;
        XrDeviceFollower _xrFollower;
        SiCharacterLoader _loader;
        SiCharacterController _controller;
        DialogueClient _client;

        bool _xrMode;
        RoomFloorPlacement _floorPlacement;
        public bool IsRoomMode => _xrMode;
        public Camera SceneCamera => _camera;
        public SiCharacterController Character => _controller;
        float _orbitYaw;
        float _orbitPitch = 8f;
        float _orbitDistance;

        // ---- Bootstrap ------------------------------------------------------

        /// <summary>
        /// Only the character scene gets this rig.
        ///
        /// <c>AfterSceneLoad</c> fires for every scene, and the smoke rig excludes
        /// this same scene for the same reason - two bootstraps that both want to
        /// own the camera would fight, and the loser would look like a broken scene
        /// rather than a scheduling problem. <see cref="SceneName"/> is the single
        /// source of truth for the name both of them compare against.
        /// </summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Bootstrap()
        {
            if (SceneManager.GetActiveScene().name != SceneName)
                return;

            if (FindAnyObjectByType<SiCharacterBootstrap>() != null)
                return;

            var root = new GameObject("MGFR Character Scene");
            root.AddComponent<SiCharacterBootstrap>();
        }

        void Awake()
        {
            _orbitDistance = orbitDistance;

            BuildCamera();
            BuildLight();
            BuildCharacter();
            BuildDialogue();
            _floorPlacement = gameObject.AddComponent<RoomFloorPlacement>();
            _floorPlacement.Bind(_cameraRig, _camera, _xrFollower, _controller);
        }

        // ---- Scene pieces ---------------------------------------------------

        void BuildCamera()
        {
            // Two levels on purpose. The rig carries the preview offset and is what
            // the mouse moves; the camera itself is driven by the head pose when a
            // headset is present, and XrDeviceFollower writes localPosition, so it
            // needs a parent to be relative to.
            var rig = new GameObject("Camera Rig");
            rig.transform.SetParent(transform, false);
            _cameraRig = rig.transform;

            var go = new GameObject("Main Camera");
            go.tag = "MainCamera";
            go.transform.SetParent(rig.transform, false);

            _camera = go.AddComponent<Camera>();
            _camera.clearFlags = CameraClearFlags.SolidColor;
            _camera.backgroundColor = KeyGreen;
            _camera.nearClipPlane = 0.05f;
            _camera.farClipPlane = 100f;
            _camera.stereoTargetEye = StereoTargetEyeMask.Both;
            _camera.allowHDR = false;
            _camera.allowMSAA = false;

            // The dialogue audio is spatialised off, but an AudioListener still has
            // to exist somewhere or nothing is audible at all.
            go.AddComponent<AudioListener>();

            _xrFollower = go.AddComponent<XrDeviceFollower>();
            _xrFollower.node = XRNode.Head;

            ApplyPreviewCamera();
        }

        void BuildLight()
        {
            var go = new GameObject("Key Light");
            go.transform.SetParent(transform, false);
            go.transform.rotation = Quaternion.Euler(35f, -25f, 0f);

            var light = go.AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = new Color(1f, 0.98f, 0.94f);
            light.intensity = 1.1f;
            light.shadows = LightShadows.None;

            // MMD models are authored against a bright, flat environment. Without
            // this the shadowed side of the face goes black and the character reads
            // as unlit rather than as lit.
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.42f, 0.42f, 0.46f);
            RenderSettings.fog = false;
        }

        void BuildCharacter()
        {
            var go = new GameObject("Si");
            go.transform.SetParent(transform, false);

            _loader = go.AddComponent<SiCharacterLoader>();
            _controller = go.AddComponent<SiCharacterController>();
            go.AddComponent<SiGroundGrid>().controller = _controller;
        }

        void BuildDialogue()
        {
            // DialogueHud has its own bootstrap that may already have run this
            // frame. Reuse whatever exists instead of creating a second client:
            // two clients would both connect, and the second one's audio would
            // arrive on a round the first one does not know about.
            _client = FindAnyObjectByType<DialogueClient>();

            if (_client == null)
            {
                var go = new GameObject("MGFR Dialogue");
                go.AddComponent<DialogueAudioOutput>();
                _client = go.AddComponent<DialogueClient>();
                go.AddComponent<DialogueHud>();
            }

            var lipSync = gameObject.AddComponent<SiDialogueLipSync>();
            lipSync.Bind(_client, _controller);
        }

        // ---- Preview camera control -----------------------------------------

        void Update()
        {
            if (!XrDeviceFollower.Suppressed && XRSettings.isDeviceActive)
            {
                if (_floorPlacement.Tick()) _xrMode = true;
            }
            // Once handed to XR, never run the orbit camera again on a dropout.
            // The tracking origin and character anchor remain fixed in the room.
            if (_xrMode) return;

            if (Input.GetMouseButton(1))
            {
                _orbitYaw += Input.GetAxis("Mouse X") * orbitSensitivity * 20f;
                _orbitPitch -= Input.GetAxis("Mouse Y") * orbitSensitivity * 20f;
                _orbitPitch = Mathf.Clamp(_orbitPitch, -80f, 80f);
            }

            var scroll = Input.GetAxis("Mouse ScrollWheel");
            if (Mathf.Abs(scroll) > 0.0001f)
            {
                _orbitDistance = Mathf.Clamp(_orbitDistance - scroll * zoomSensitivity, 0.4f, 12f);
            }

            if (Input.GetKeyDown(KeyCode.G))
                showGroundGrid = !showGroundGrid;

            ApplyPreviewCamera();
        }

        public void EnterRoomMode()
        {
            if (_floorPlacement == null) return;
            _floorPlacement.EnterFromCurrentPose();
            _xrMode = _floorPlacement.RoomReady;
        }

        void ApplyPreviewCamera()
        {
            var target = _controller != null
                ? _controller.transform.position + Vector3.up * (1.1f * _controller.CharacterScale)
                : Vector3.up * 1.1f;

            var rotation = Quaternion.Euler(_orbitPitch, _orbitYaw, 0f);
            _cameraRig.position = target + rotation * new Vector3(0f, 0f, -_orbitDistance);
            _cameraRig.rotation = rotation;
        }
    }

    /// <summary>
    /// An optional wireframe grid at the character's ground height.
    ///
    /// Drawn with GL rather than as a mesh because a plane would be an opaque
    /// object in front of the real room in the headset. Lines cost nothing and are
    /// invisible when the feature is off, which is the default.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SiGroundGrid : MonoBehaviour
    {
        public SiCharacterController controller;

        [Tooltip("Half-extent of the grid in metres.")]
        public float extent = 2.5f;
        public float spacing = 0.5f;
        public Color colour = new Color(1f, 1f, 1f, 0.25f);

        Material _material;

        void OnRenderObject()
        {
            var bootstrap = FindAnyObjectByType<SiCharacterBootstrap>();
            if (bootstrap == null || !bootstrap.showGroundGrid)
                return;
            if (controller == null)
                return;

            if (_material == null)
            {
                var shader = Shader.Find("Hidden/Internal-Colored");
                if (shader == null)
                    return;

                _material = new Material(shader) { hideFlags = HideFlags.HideAndDontSave };
                _material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
                _material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
                _material.SetInt("_Cull", (int)CullMode.Off);
                _material.SetInt("_ZWrite", 0);
            }

            _material.SetPass(0);

            var y = controller.GroundHeight + 0.001f;
            var x0 = controller.PlanarPosition.x - extent;
            var x1 = controller.PlanarPosition.x + extent;
            var z0 = controller.PlanarPosition.z - extent;
            var z1 = controller.PlanarPosition.z + extent;

            GL.PushMatrix();
            GL.Begin(GL.LINES);
            GL.Color(colour);

            for (var x = Mathf.Ceil(x0 / spacing) * spacing; x <= x1; x += spacing)
            {
                GL.Vertex3(x, y, z0);
                GL.Vertex3(x, y, z1);
            }

            for (var z = Mathf.Ceil(z0 / spacing) * spacing; z <= z1; z += spacing)
            {
                GL.Vertex3(x0, y, z);
                GL.Vertex3(x1, y, z);
            }

            GL.End();
            GL.PopMatrix();
        }
    }
}
