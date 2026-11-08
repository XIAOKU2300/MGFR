using System;
using System.Text;
using UnityEngine;
using UnityEngine.XR;

namespace MGFR.Dialogue
{
    /// <summary>
    /// A readout and a set of controls for the dialogue client, drawn with IMGUI.
    ///
    /// IMGUI is used because the project has no uGUI in it and adding the whole
    /// Canvas stack for a debug panel would be out of proportion. OnGUI also draws
    /// into the desktop mirror window for free, which is what makes it usable while
    /// wearing a headset: the panel is visible in the mirror, and the headset shows
    /// the same scene.
    ///
    /// Nothing here may throw. A throw inside OnGUI leaves IMGUI in a broken state
    /// for the rest of the frame, so every entry point is guarded.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class DialogueHud : MonoBehaviour
    {
        const string PromptControl = "mgfr-dialogue-prompt";
        const int FontSize = 14;
        const int PanelWidth = 620;
        const int PanelHeight = 560;

        // Long replies would otherwise grow the panel without bound; only the tail
        // is shown, which is the part still being written.
        const int MaxReplyChars = 600;

        [SerializeField] DialogueClient _client;

        string _url = DialogueClient.DefaultUrl;
        string _prompt = "";
        string _lastError = "";
        bool _promptHasFocus;

        /// <summary>
        /// The only scene this panel belongs in.
        ///
        /// It used to bootstrap everywhere, which quietly put a dialogue client and
        /// a 620x560 panel on top of the smoke test. The smoke test is the
        /// regression baseline for the whole project, so anything that changes what
        /// it draws has to be kept out of it. <c>SiCharacterBootstrap</c> creates
        /// the same three components if this did not get there first.
        /// </summary>
        const string CharacterSceneName = "SiCharacter";

        /// <summary>
        /// Creates the dialogue objects if the scene has none, so the HUD works in
        /// the character scene without anything being wired up by hand.
        /// </summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Bootstrap()
        {
            if (UnityEngine.SceneManagement.SceneManager.GetActiveScene().name != CharacterSceneName)
                return;

            if (FindAnyObjectByType<DialogueHud>() != null)
                return;

            var go = new GameObject("MGFR Dialogue");
            DontDestroyOnLoad(go);

            // Order matters: the client finds the audio output in its own Awake.
            go.AddComponent<DialogueAudioOutput>();
            go.AddComponent<DialogueClient>();
            go.AddComponent<DialogueHud>();
        }

        void Awake()
        {
            if (_client == null)
                _client = GetComponent<DialogueClient>();
        }

        void Update()
        {
            try
            {
                HandleKeys();
            }
            catch (Exception e)
            {
                _lastError = e.GetType().Name + ": " + e.Message;
            }
        }

        /// <summary>
        /// Keyboard shortcuts. They are suppressed while the text field has focus so
        /// that typing a prompt does not trigger connect or interrupt.
        /// </summary>
        void HandleKeys()
        {
            if (_client == null)
                return;

            if (!_promptHasFocus)
            {
                if (Input.GetKeyDown(KeyCode.C))
                    _client.Connect(_url);
                if (Input.GetKeyDown(KeyCode.D))
                    _client.Disconnect();
                if (Input.GetKeyDown(KeyCode.S))
                    _client.StartSession();
                if (Input.GetKeyDown(KeyCode.E))
                    _client.EndSession();
                if (Input.GetKeyDown(KeyCode.I))
                    _client.Interrupt();
                if (Input.GetKeyDown(KeyCode.P))
                    _client.SendPing();
            }

            if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter))
                SendPrompt();
        }

        void SendPrompt()
        {
            if (_client == null || string.IsNullOrEmpty(_prompt))
                return;

            _client.SendTextPrompt(_prompt);
            _prompt = "";
        }

        void OnGUI()
        {
            try
            {
                Draw();
            }
            catch (Exception e)
            {
                // Record it and stop drawing this frame rather than letting the
                // exception escape into IMGUI.
                _lastError = e.GetType().Name + ": " + e.Message;
            }
        }

        void Draw()
        {
            GUI.skin.label.fontSize = FontSize;
            GUI.skin.button.fontSize = FontSize;
            GUI.skin.textField.fontSize = FontSize;

            var area = new Rect(12f, 12f, PanelWidth, PanelHeight);
            GUILayout.BeginArea(area, GUI.skin.box);

            GUILayout.Label("MGFR dialogue");

            if (_client == null)
            {
                GUILayout.Label("No DialogueClient on this object.");
                GUILayout.EndArea();
                return;
            }

            // The one line that says whether this is being seen in a headset or on
            // the desktop mirror. Without an active device there is no stereo view,
            // so what is on screen is a flat preview.
            GUILayout.Label(XRSettings.isDeviceActive
                ? "Display: XR headset active"
                : "Display: desktop preview (no XR device)");

            GUILayout.Label("State: " + _client.State);
            GUILayout.Label("Status: " + _client.StatusLine);

            string serverState = _client.ServerState;
            if (!string.IsNullOrEmpty(_client.ServerDetail))
                serverState += " (" + _client.ServerDetail + ")";
            GUILayout.Label("Server state: " + (string.IsNullOrEmpty(serverState) ? "-" : serverState));

            GUILayout.Label("Round: " + _client.CurrentRound);
            GUILayout.Label("Server: " + (string.IsNullOrEmpty(_client.ServerVersion) ? "-" : _client.ServerVersion));
            GUILayout.Label("TTS: " + _client.TtsSampleRate + " Hz x" + _client.TtsChannels);

            GUILayout.Label("ASR: " + (string.IsNullOrEmpty(_client.LastAsrText) ? "-" : _client.LastAsrText));
            GUILayout.Label("Reply: " + Tail(_client.ReplyText, MaxReplyChars));

            GUILayout.Label("Speaking: " + (_client.IsSpeaking ? "yes" : "no") +
                            "   level " + _client.CurrentLevel.ToString("0.00"));

            GUILayout.Label("Audio queued: " + _client.QueuedSamples +
                            "   dropped frames: " + _client.DroppedAudioFrames +
                            "   dropped samples: " + _client.DroppedSamples);

            if (!string.IsNullOrEmpty(_client.LastError))
                GUILayout.Label("Last error: " + _client.LastError);

            if (!string.IsNullOrEmpty(_lastError))
                GUILayout.Label("HUD error: " + _lastError);

            GUILayout.Space(6f);

            GUILayout.BeginHorizontal();
            GUILayout.Label("URL", GUILayout.Width(36f));
            _url = GUILayout.TextField(_url ?? "", GUILayout.Width(PanelWidth - 90f));
            GUILayout.EndHorizontal();

            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Connect"))
                _client.Connect(_url);
            if (GUILayout.Button("Disconnect"))
                _client.Disconnect();
            GUILayout.EndHorizontal();

            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Start session"))
                _client.StartSession();
            if (GUILayout.Button("End session"))
                _client.EndSession();
            if (GUILayout.Button("Interrupt"))
                _client.Interrupt();
            if (GUILayout.Button("Ping"))
                _client.SendPing();
            GUILayout.EndHorizontal();

            GUILayout.BeginHorizontal();
            GUI.SetNextControlName(PromptControl);
            _prompt = GUILayout.TextField(_prompt ?? "", GUILayout.Width(PanelWidth - 160f));
            if (GUILayout.Button("Send text"))
                SendPrompt();
            GUILayout.EndHorizontal();

            GUILayout.Label("Keys: C connect, D disconnect, S start, E end, I interrupt, P ping, Enter send");

            // Read after the field is drawn, so it reflects this frame. It is used
            // by the next Update to decide whether the hotkeys should be live.
            _promptHasFocus = GUI.GetNameOfFocusedControl() == PromptControl;

            GUILayout.EndArea();
        }

        /// <summary>Returns the last <paramref name="max"/> characters, prefixed with an ellipsis when trimmed.</summary>
        static string Tail(string value, int max)
        {
            if (string.IsNullOrEmpty(value))
                return "-";
            if (value.Length <= max)
                return value;

            return "..." + value.Substring(value.Length - max);
        }
    }
}
