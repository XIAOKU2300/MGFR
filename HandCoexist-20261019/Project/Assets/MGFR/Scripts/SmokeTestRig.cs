using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.XR;

namespace MGFR.SmokeTest
{
    /// <summary>
    /// Milestone ①'s hardware smoke test: a solid key-green background, one white
    /// object, head and physical-controller tracking, and a test tone.
    ///
    /// The whole rig is built in code rather than saved in a scene, so the scene
    /// stays empty and there is exactly one place where the test is defined. Run
    /// MGFR > Create Smoke Test Scene once to make an (empty) scene and put it in
    /// Build Settings; pressing Play in any scene works too.
    ///
    /// What this does NOT test: passthrough, the headset microphone, bare-hand
    /// tracking. Those are separate single-variable runs — see docs/acceptance.md.
    /// </summary>
    public sealed class SmokeTestRig : MonoBehaviour
    {
        // ---- Tunables -------------------------------------------------------

        /// <summary>
        /// Pure green, and the exact value ALVR's RgbChromaKey is configured to
        /// key out. Nothing else in the scene may use this colour, and no
        /// post-processing may sit between the camera and the encoder while the
        /// key is on.
        /// </summary>
        static readonly Color KeyGreen = new Color(0f, 1f, 0f, 1f);

        static readonly Color TrackedColour = new Color(1f, 1f, 1f, 1f);
        static readonly Color UntrackedColour = new Color(0.35f, 0.05f, 0.05f, 1f);

        const float TargetCubeSize = 0.25f;
        const float TargetDistance = 1.5f;
        const float TargetSpinDegreesPerSecond = 30f;

        const float HandCubeSize = 0.08f;

        const float ToneFrequency = 440f;
        const float ToneSeconds = 1f;
        const float ToneAmplitude = 0.25f;
        const int ToneSampleRate = 48000;

        const float ReportIntervalSeconds = 10f;

        // ---- Construction ---------------------------------------------------

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Bootstrap()
        {
            // Stay out of the character scene. BuildCamera below disables every
            // camera and every AudioListener already in the scene, so without this
            // gate the smoke rig would disable the character's preview camera and
            // its listener, add a second MainCamera, and drop a spinning cube into
            // the middle of the character scene.
            //
            // This is an exclusion rather than an allow list on purpose: pressing
            // Play in an empty scene, or in SmokeTest.unity, still gives the smoke
            // test exactly as before. The scene name is read from
            // SiCharacterBootstrap so the two cannot drift apart.
            if (SceneManager.GetActiveScene().name == MGFR.Character.SiCharacterBootstrap.SceneName)
                return;

            if (FindAnyObjectByType<SmokeTestRig>() != null)
                return;

            var root = new GameObject("MGFR Smoke Test");
            DontDestroyOnLoad(root);
            root.AddComponent<SmokeTestRig>();
        }

        Camera _camera;
        XrDeviceFollower _head;
        XrDeviceFollower _leftHand;
        XrDeviceFollower _rightHand;
        GameObject _targetCube;
        Renderer _leftHandRenderer;
        Renderer _rightHandRenderer;
        AudioSource _audio;
        AudioClip _tone;

        bool _targetPlaced;
        float _lastReport;
        int _toneCount;

        void Awake()
        {
            // Keep rendering while the desktop window is not focused. Without
            // this the headset view freezes the moment you click elsewhere.
            Application.runInBackground = true;
            QualitySettings.vSyncCount = 0;

            _camera = BuildCamera(out _head);
            BuildLight();

            _targetCube = BuildCube("Target Cube", TargetCubeSize);
            Paint(_targetCube, TrackedColour);

            var left = BuildCube("Left Hand", HandCubeSize);
            _leftHandRenderer = left.GetComponent<Renderer>();
            _leftHand = AttachFollower(left, XRNode.LeftHand);

            var right = BuildCube("Right Hand", HandCubeSize);
            _rightHandRenderer = right.GetComponent<Renderer>();
            _rightHand = AttachFollower(right, XRNode.RightHand);

            left.transform.localPosition = new Vector3(-0.25f, 1.10f, 0.35f);
            right.transform.localPosition = new Vector3(0.25f, 1.10f, 0.35f);

            BuildTone();
            ReportEnvironment();
        }

        Camera BuildCamera(out XrDeviceFollower head)
        {
            // A template scene usually ships its own camera and AudioListener.
            // Ours is the only one that should render or listen.
            foreach (var existing in FindObjectsByType<Camera>(FindObjectsSortMode.None))
                existing.enabled = false;

            foreach (var existing in FindObjectsByType<AudioListener>(FindObjectsSortMode.None))
                existing.enabled = false;

            var go = new GameObject("MGFR Camera");
            go.transform.SetParent(transform, false);
            go.tag = "MainCamera";

            var camera = go.AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = KeyGreen;
            camera.nearClipPlane = 0.05f;
            camera.farClipPlane = 100f;
            camera.stereoTargetEye = StereoTargetEyeMask.Both;

            // Both of these can shift the background off the exact keyed value.
            // Turning them off is also how we isolate the key from anti-aliasing:
            // whether the cube's edges survive the key with MSAA on is a later,
            // separate question.
            camera.allowHDR = false;
            camera.allowMSAA = false;

            go.AddComponent<AudioListener>();

            head = go.AddComponent<XrDeviceFollower>();
            head.node = XRNode.Head;
            return camera;
        }

        void BuildLight()
        {
            var go = new GameObject("MGFR Light");
            go.transform.SetParent(transform, false);
            go.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            var light = go.AddComponent<Light>();
            light.type = LightType.Directional;
            light.color = Color.white;
            light.intensity = 1f;

            // Shadows cost frames and prove nothing about the link.
            light.shadows = LightShadows.None;
        }

        GameObject BuildCube(string name, float size)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(transform, false);
            go.transform.localScale = Vector3.one * size;

            // Nothing here is meant to be touched or collided with.
            var collider = go.GetComponent<Collider>();
            if (collider != null)
                Destroy(collider);

            return go;
        }

        static XrDeviceFollower AttachFollower(GameObject go, XRNode node)
        {
            var follower = go.AddComponent<XrDeviceFollower>();
            follower.node = node;
            return follower;
        }

        /// <summary>
        /// Colours a primitive's own material instance. CreatePrimitive already
        /// assigns whichever material the active render pipeline wants, so this
        /// works the same under URP and under the built-in pipeline.
        /// </summary>
        static void Paint(GameObject go, Color colour)
        {
            var renderer = go.GetComponent<Renderer>();
            if (renderer == null)
                return;

            renderer.material.color = colour;
        }

        void BuildTone()
        {
            _tone = BuildToneClip();
            _audio = gameObject.AddComponent<AudioSource>();
            _audio.playOnAwake = false;
            _audio.clip = _tone;
            _audio.volume = 1f;

            // 2D on purpose: this tests the path from the application to the
            // headset speakers, not Unity's spatialiser.
            _audio.spatialBlend = 0f;
        }

        static AudioClip BuildToneClip()
        {
            int count = Mathf.RoundToInt(ToneSampleRate * ToneSeconds);
            var samples = new float[count];
            int fade = Mathf.Max(1, Mathf.RoundToInt(ToneSampleRate * 0.01f));

            for (int i = 0; i < count; i++)
            {
                float envelope = 1f;
                if (i < fade)
                    envelope = (float)i / fade;
                else if (i >= count - fade)
                    envelope = (float)(count - 1 - i) / fade;

                samples[i] = Mathf.Sin(2f * Mathf.PI * ToneFrequency * i / ToneSampleRate)
                             * ToneAmplitude * envelope;
            }

            var clip = AudioClip.Create("MGFR test tone", count, 1, ToneSampleRate, false);
            clip.SetData(samples, 0);
            return clip;
        }

        // ---- Per frame ------------------------------------------------------

        void Update()
        {
            UpdateHandColour(_leftHand, _leftHandRenderer);
            UpdateHandColour(_rightHand, _rightHandRenderer);

            PlaceTargetOnce();

            _targetCube.transform.localRotation =
                Quaternion.Euler(0f, Time.time * TargetSpinDegreesPerSecond, 0f);

            PlayToneOnButton();
            ReportPeriodically();
        }

        static void UpdateHandColour(XrDeviceFollower follower, Renderer renderer)
        {
            if (renderer == null)
                return;

            var wanted = follower.IsTracked ? TrackedColour : UntrackedColour;
            if (renderer.material.color != wanted)
                renderer.material.color = wanted;
        }

        /// <summary>
        /// Puts the target cube at the wearer's eye height, 1.5 m ahead, the first
        /// time the head is tracked. Doing it from the measured head pose rather
        /// than from a fixed y means it is right whichever tracking origin ALVR
        /// is using, floor-relative or eye-relative.
        /// </summary>
        void PlaceTargetOnce()
        {
            if (_targetPlaced || !_head.IsTracked)
                return;

            _targetPlaced = true;

            var head = _head.transform;
            var forward = Vector3.ProjectOnPlane(head.forward, Vector3.up);
            if (forward.sqrMagnitude < 0.25f)
                forward = Vector3.forward;
            forward.Normalize();

            _targetCube.transform.localPosition = head.localPosition + forward * TargetDistance;
            _targetCube.transform.localRotation = Quaternion.identity;

            Debug.Log($"[MGFR] head is tracked; eye height {head.localPosition.y:F3} m, " +
                      $"target cube placed at {_targetCube.transform.localPosition}.");
        }

        void PlayToneOnButton()
        {
            string button = null;
            if (_rightHand.ButtonPressedThisFrame)
                button = $"right {_rightHand.PressedButton}";
            else if (_leftHand.ButtonPressedThisFrame)
                button = $"left {_leftHand.PressedButton}";

            if (button == null)
                return;

            _toneCount++;
            _audio.PlayOneShot(_tone);
            Debug.Log($"[MGFR] test tone {_toneCount} on {button}, at {Time.time:F1}s.");
        }

        void ReportPeriodically()
        {
            if (Time.time - _lastReport < ReportIntervalSeconds)
                return;

            _lastReport = Time.time;
            Debug.Log($"[MGFR] t={Time.time:F0}s frame={Time.deltaTime * 1000f:F1}ms " +
                      $"head={Tracked(_head)} left={Tracked(_leftHand)} right={Tracked(_rightHand)} " +
                      $"tones={_toneCount}");
        }

        static string Tracked(XrDeviceFollower follower) => follower.IsTracked ? "ok" : "no";

        void ReportEnvironment()
        {
            string pipeline = GraphicsSettings.defaultRenderPipeline == null
                ? "built-in"
                : GraphicsSettings.defaultRenderPipeline.GetType().Name;

            Debug.Log($"[MGFR] smoke test started. Unity {Application.unityVersion}, " +
                      $"pipeline {pipeline}, colour space {QualitySettings.activeColorSpace}, " +
                      $"audio out {AudioSettings.outputSampleRate} Hz, " +
                      $"XR active {XRSettings.isDeviceActive}, " +
                      $"background {ColorUtility.ToHtmlStringRGB(KeyGreen)}.");
        }
    }
}
