using System;
using MGFR.Dialogue;
using UnityEngine;
using UnityEngine.XR;

namespace MGFR.Character
{
    /// <summary>
    /// Placement, blinking and mouth movement for the 祀 character.
    ///
    /// Everything here is meant to be driven from the keyboard with no headset
    /// attached, because that is the only way this can be iterated on: putting a
    /// headset on to check whether the character is 3 cm too high is not a loop
    /// anyone can work in. The headset path exists (the preview camera carries an
    /// <c>XrDeviceFollower</c>) but it is unverified - see the marker in
    /// docs/acceptance.md.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SiCharacterController : MonoBehaviour
    {
        // ---- Tunables -------------------------------------------------------

        [SerializeField] SiCharacterLoader _loader;

        [Header("Placement")]
        [Tooltip("Metres per second for the arrow keys.")]
        public float moveSpeed = 0.6f;
        [Tooltip("Degrees per second for the left/right arrow keys.")]
        public float turnSpeed = 60f;
        [Tooltip("Multiplier change per second for - and =.")]
        public float scaleSpeed = 0.5f;
        public float minScale = 0.2f;
        public float maxScale = 4f;
        public float minGroundHeight = -1f;
        public float maxGroundHeight = 3f;

        [Header("Blink")]
        public bool autoBlink = true;
        public float blinkIntervalMin = 2.5f;
        public float blinkIntervalMax = 6f;
        public float blinkDuration = 0.13f;

        [Header("Mouth")]
        [Tooltip("Multiplies the audio level before it becomes mouth opening.")]
        public float mouthGain = 8f;
        [Tooltip("How fast the mouth follows the audio, in units per second.")]
        public float mouthSmoothing = 20f;

        [Header("Defaults restored by Reset Placement")]
        public Vector3 defaultPosition = Vector3.zero;
        // The measured model front is -Z; the default preview camera is at -Z.
        public float defaultYaw = 0f;
        public float defaultScale = 1f;
        public float defaultGroundHeight = 0f;

        // ---- State ----------------------------------------------------------

        public float Yaw { get; private set; }
        public float CharacterScale { get; private set; } = 1f;
        public float GroundHeight { get; private set; }
        public Vector3 PlanarPosition { get; private set; }

        /// <summary>Current mouth opening, 0..1.</summary>
        public float MouthOpen { get; private set; }
        /// <summary>Current blink, 0..1.</summary>
        public float Blink { get; private set; }

        public string LastAction { get; private set; } = "ready";

        SiCharacterLoader Loader => _loader != null ? _loader : (_loader = GetComponent<SiCharacterLoader>());

        float _blinkTimer;
        float _blinkPhase = -1f;
        float _oscillation;
        string _hudError = "";

        void Awake()
        {
            if (_loader == null)
                _loader = GetComponent<SiCharacterLoader>();
        }

        void Start()
        {
            ResetPlacement();
            _blinkTimer = UnityEngine.Random.Range(blinkIntervalMin, blinkIntervalMax);
        }

        void Update()
        {
            HandleKeys();
            ApplyPlacement();
            UpdateBlink();
            ApplyMouth();
        }

        // ---- Placement ------------------------------------------------------

        public void ResetPlacement()
        {
            PlanarPosition = defaultPosition;
            Yaw = defaultYaw;
            CharacterScale = defaultScale;
            GroundHeight = defaultGroundHeight;
            LastAction = "placement reset";
            ApplyPlacement();
        }

        /// <summary>Set a room-space anchor once. Head motion never updates it.</summary>
        public void PlaceInFrontOf(Vector3 viewerPosition, Vector3 viewerForward, float distance)
        {
            PlaceOnGround(viewerPosition, viewerForward, distance, GroundHeight);
        }

        public void PlaceOnGround(Vector3 viewerPosition, Vector3 viewerForward, float distance, float groundHeight)
        {
            if (!float.IsFinite(viewerPosition.sqrMagnitude) || !float.IsFinite(viewerForward.sqrMagnitude) ||
                !float.IsFinite(groundHeight) || !float.IsFinite(distance)) return;
            var forward = Vector3.ProjectOnPlane(viewerForward, Vector3.up);
            if (forward.sqrMagnitude < 0.01f) forward = Vector3.forward;
            forward.Normalize();
            var position = viewerPosition + forward * Mathf.Clamp(distance, 0.6f, 5f);
            defaultPosition = new Vector3(position.x, 0f, position.z);
            defaultGroundHeight = groundHeight;
            defaultScale = CharacterScale;
            // The model's visible front is -Z, the opposite of Transform.forward.
            defaultYaw = Quaternion.LookRotation(forward, Vector3.up).eulerAngles.y;
            ResetPlacement();
            LastAction = "room anchor placed once, facing initial viewer";
            Debug.Log($"[MGFR VR fix] room anchor={transform.position:F3} yaw={Yaw:F1}; fixed until explicit reposition");
        }

        public void AdjustRoomPlacement(Vector3 movement, float yaw, float scale, float ground)
        {
            if (!float.IsFinite(movement.sqrMagnitude) || !float.IsFinite(yaw) || !float.IsFinite(scale) || !float.IsFinite(ground)) return;
            PlanarPosition += movement;
            Yaw = Mathf.Repeat(Yaw + yaw, 360f);
            CharacterScale = Mathf.Clamp(CharacterScale + scale, minScale, maxScale);
            GroundHeight = Mathf.Clamp(GroundHeight + ground, minGroundHeight, maxGroundHeight);
            LastAction = "controller placement"; ApplyPlacement();
        }
        public void RememberRoomPlacement()
        {
            defaultPosition = PlanarPosition; defaultYaw = Yaw;
            defaultScale = CharacterScale; defaultGroundHeight = GroundHeight;
        }
        public void RestoreRoomPlacement(Vector3 position, float yaw, float scale, float ground)
        {
            if (!float.IsFinite(position.sqrMagnitude) || !float.IsFinite(yaw) || !float.IsFinite(scale) || !float.IsFinite(ground)) return;
            PlanarPosition = position; Yaw = yaw;
            CharacterScale = scale; GroundHeight = ground; ApplyPlacement();
        }

        void ApplyPlacement()
        {
            transform.position = new Vector3(PlanarPosition.x, GroundHeight, PlanarPosition.z);
            // The model's feet are at y = 0 in its own space, so putting the root
            // at the ground height puts the feet on the ground. That was measured,
            // not assumed: convert_si.py reports scaled bounds y -0.000 .. 1.793.
            transform.rotation = Quaternion.Euler(0f, Yaw, 0f);
            transform.localScale = Vector3.one * CharacterScale;
        }

        void HandleKeys()
        {
            // Deliberately no overlap with DialogueHud's hotkeys (C D S E I P and
            // Return). Two components reading the same key in the same frame is a
            // bug that only shows up as "the character twitches when I press
            // Interrupt".
            var dt = Time.deltaTime;
            var forward = Vector3.forward * (CharacterScale);
            var right = Vector3.right * (CharacterScale);

            if (Input.GetKey(KeyCode.UpArrow))
            {
                PlanarPosition += forward * (moveSpeed * dt);
                LastAction = "moved forward";
            }
            if (Input.GetKey(KeyCode.DownArrow))
            {
                PlanarPosition -= forward * (moveSpeed * dt);
                LastAction = "moved back";
            }
            if (Input.GetKey(KeyCode.Z))
            {
                PlanarPosition -= right * (moveSpeed * dt);
                LastAction = "strafed left";
            }
            if (Input.GetKey(KeyCode.X))
            {
                PlanarPosition += right * (moveSpeed * dt);
                LastAction = "strafed right";
            }
            if (Input.GetKey(KeyCode.LeftArrow))
            {
                Yaw -= turnSpeed * dt;
                LastAction = "turned left";
            }
            if (Input.GetKey(KeyCode.RightArrow))
            {
                Yaw += turnSpeed * dt;
                LastAction = "turned right";
            }
            if (Input.GetKey(KeyCode.PageUp))
            {
                GroundHeight = Mathf.Min(maxGroundHeight, GroundHeight + moveSpeed * dt);
                LastAction = "raised";
            }
            if (Input.GetKey(KeyCode.PageDown))
            {
                GroundHeight = Mathf.Max(minGroundHeight, GroundHeight - moveSpeed * dt);
                LastAction = "lowered";
            }
            if (Input.GetKey(KeyCode.Minus))
            {
                CharacterScale = Mathf.Max(minScale, CharacterScale - scaleSpeed * dt);
                LastAction = "scaled down";
            }
            if (Input.GetKey(KeyCode.Equals))
            {
                CharacterScale = Mathf.Min(maxScale, CharacterScale + scaleSpeed * dt);
                LastAction = "scaled up";
            }
            if (Input.GetKeyDown(KeyCode.Home))
            {
                ResetPlacement();
            }
            if (Input.GetKeyDown(KeyCode.B))
            {
                TriggerBlink();
                LastAction = "blinked";
            }
            if (Input.GetKeyDown(KeyCode.Alpha0))
            {
                ClearExpression();
                LastAction = "expression cleared";
            }

            // 1..5 drive the five vowels directly, which is how the lip sync is
            // checked without needing the service to be up.
            for (var i = 0; i < 5; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                {
                    TestVowel(i);
                    LastAction = "test vowel " + (i + 1);
                }
            }

            if (Input.GetKeyDown(KeyCode.Alpha6))
            {
                ToggleBlush();
                LastAction = "toggled 照れ (material morph)";
            }
        }

        // ---- Blink ----------------------------------------------------------

        public void TriggerBlink()
        {
            _blinkPhase = 0f;
        }

        void UpdateBlink()
        {
            var loader = Loader;
            if (loader == null || !loader.IsReady)
                return;

            if (_blinkPhase >= 0f)
            {
                _blinkPhase += Time.deltaTime / Mathf.Max(0.01f, blinkDuration);
                if (_blinkPhase >= 1f)
                {
                    _blinkPhase = -1f;
                    Blink = 0f;
                    _blinkTimer = UnityEngine.Random.Range(blinkIntervalMin, blinkIntervalMax);
                }
                else
                {
                    // Half a sine: shut and open again, with the velocity zero at
                    // both ends so it does not snap.
                    Blink = Mathf.Sin(Mathf.PI * _blinkPhase);
                }
            }
            else if (autoBlink)
            {
                _blinkTimer -= Time.deltaTime;
                if (_blinkTimer <= 0f)
                    _blinkPhase = 0f;
                Blink = 0f;
            }

            var index = loader.FindBlendShape("まばたき");
            if (index >= 0)
                loader.SetBlendShape(index, Blink * 100f);
        }

        // ---- Mouth ----------------------------------------------------------

        /// <summary>
        /// Called by the lip sync adapter with the level of the audio that is
        /// actually being played, and whether anything is playing at all.
        ///
        /// This is amplitude driven, not phoneme driven. It satisfies "the mouth is
        /// driven by the audio that is really playing" and it closes when playback
        /// stops, is interrupted, or the connection drops - but it does not know
        /// which sound is being made, so it is not viseme recognition and is not
        /// reported as such.
        /// </summary>
        public void SetMouth(float level01, bool speaking)
        {
            _mouthInput = Mathf.Clamp01(level01);
            _mouthSpeaking = speaking;
        }

        float _mouthInput;
        bool _mouthSpeaking;

        void ApplyMouth()
        {
            var loader = Loader;
            if (loader == null || !loader.IsReady)
                return;

            var target = _mouthSpeaking ? Mathf.Clamp01(_mouthInput * mouthGain) : 0f;
            MouthOpen = Mathf.MoveTowards(MouthOpen, target, mouthSmoothing * Time.deltaTime);

            // A slow wobble so a long sentence does not hold one frozen shape.
            // Summed with the primary vowel it stays inside 0..1 of total opening.
            _oscillation = Mathf.Repeat(_oscillation + Time.deltaTime * (0.7f + MouthOpen), 2f);

            var wide = MouthOpen;
            var narrow = MouthOpen * Mathf.Clamp01(Mathf.Sin(Mathf.PI * _oscillation) * 0.6f);

            loader.SetBlendShape("あ", wide * 100f);
            loader.SetBlendShape("い", narrow * 100f);
            // ん is the closed-mouth shape; it is held at zero here because the rest
            // pose already has the mouth closed. Keeping the call documents that the
            // shape exists and is deliberately unused.
            loader.SetBlendShape("ん", 0f);
        }

        void TestVowel(int index)
        {
            var loader = Loader;
            if (loader == null || !loader.IsReady)
                return;

            loader.ZeroBlendShapes();
            var vowels = new[] { "あ", "い", "う", "え", "お" };
            loader.SetBlendShape(vowels[index], 100f);
            MouthOpen = 0f;
        }

        public void ClearExpression()
        {
            var loader = Loader;
            if (loader == null || !loader.IsReady)
                return;
            loader.ZeroBlendShapes();
            loader.BlushWeight = 0f;
            MouthOpen = 0f;
        }

        public void ToggleBlush()
        {
            var loader = Loader;
            if (loader == null || !loader.IsReady)
                return;
            loader.BlushWeight = loader.BlushWeight > 0.5f ? 0f : 1f;
        }

        // ---- HUD ------------------------------------------------------------

        void OnGUI()
        {
            try
            {
                DrawHud();
            }
            catch (Exception e)
            {
                // A throw inside OnGUI leaves IMGUI half-built for the rest of the
                // frame, which takes the dialogue panel down with it.
                _hudError = e.GetType().Name + ": " + e.Message;
            }
        }

        void DrawHud()
        {
            // Right-aligned, because DialogueHud owns the left 620x560 and two
            // panels drawn over each other are unreadable.
            const float width = 430f;
            const float height = 470f;
            var area = new Rect(Screen.width - width - 12f, 12f, width, height);

            GUI.skin.label.fontSize = 14;
            GUI.skin.button.fontSize = 14;

            GUILayout.BeginArea(area, GUI.skin.box);

            GUILayout.Label("MGFR character - 祀");

            // The same distinction the dialogue panel makes, repeated here because
            // this is the panel someone reads while adjusting the character.
            GUILayout.Label(XRSettings.isDeviceActive
                ? "Display: XR headset active (headset path UNVERIFIED)"
                : "Display: desktop preview (no XR device)");

            var loader = Loader;
            if (loader == null)
            {
                GUILayout.Label("Model: no SiCharacterLoader on this object.");
            }
            else if (!loader.IsReady)
            {
                GUILayout.Label("Model: NOT BUILT");
                GUILayout.Label(loader.Status ?? "");
            }
            else
            {
                GUILayout.Label("Model: " + loader.Status);
                var bounds = loader.LocalBounds;
                GUILayout.Label($"Height: {bounds.size.y:F3} m   verts: {loader.Data.counts.vertices:N0}"
                              + $"   blend shapes: {loader.BlendShapeCount}");
                GUILayout.Label($"Materials: {loader.Materials.Length}"
                              + $"   material morphs: {string.Join(", ", loader.MaterialMorphNames)}");
            }

            GUILayout.Space(4f);
            GUILayout.Label("Placement");
            GUILayout.Label($"  position  x {PlanarPosition.x:F2}  z {PlanarPosition.z:F2}");
            GUILayout.Label($"  yaw {Yaw:F1} deg   scale {CharacterScale:F2}   ground y {GroundHeight:F2}");
            GUILayout.Label($"  mouth {MouthOpen:F2}   blink {Blink:F2}   " + (_mouthSpeaking ? "speaking" : "silent"));
            GUILayout.Label("  last: " + LastAction);

            var client = FindAnyObjectByType<DialogueClient>();
            GUILayout.Label(client == null
                ? "Service: no dialogue client in this scene"
                : $"Service: {client.State} / server {client.ServerState} / round {client.CurrentRound}");

            if (!string.IsNullOrEmpty(_hudError))
                GUILayout.Label("HUD error: " + _hudError);

            GUILayout.Space(6f);

            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Reset placement"))
                ResetPlacement();
            if (GUILayout.Button("Blink"))
                TriggerBlink();
            if (GUILayout.Button("Clear"))
                ClearExpression();
            GUILayout.EndHorizontal();

            GUILayout.BeginHorizontal();
            if (GUILayout.Button("あ")) TestVowel(0);
            if (GUILayout.Button("い")) TestVowel(1);
            if (GUILayout.Button("う")) TestVowel(2);
            if (GUILayout.Button("え")) TestVowel(3);
            if (GUILayout.Button("お")) TestVowel(4);
            if (GUILayout.Button("照れ")) ToggleBlush();
            GUILayout.EndHorizontal();

            GUILayout.Label("Arrows: move / turn.  Z X: strafe.  PageUp/Down: ground height.");
            GUILayout.Label("Minus / Equals: scale.  Home: reset.  B: blink.  1-5: vowels.  6: 照れ.");
            GUILayout.Label("Right-drag the preview: orbit.  Scroll: zoom.  (Desktop only.)");

            GUILayout.EndArea();
        }
    }
}
