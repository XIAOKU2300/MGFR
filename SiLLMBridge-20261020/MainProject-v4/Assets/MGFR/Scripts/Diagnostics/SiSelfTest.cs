using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.SmokeTest;
using UnityEngine;
using UnityEngine.Profiling;
using UnityEngine.XR;

namespace MGFR.Diagnostics
{
    /// <summary>
    /// A command-line driven self test and soak harness for the packaged player.
    ///
    /// It exists because the desktop preview cannot be driven by hand in a build:
    /// the HUD needs a mouse and a keyboard, and a script has neither. Launched
    /// with <c>-mgfr-selftest</c> this component connects to the dialogue service,
    /// starts a session, sends text prompts, and writes down what actually
    /// happened - the level the audio mixer really produced, how long the reply
    /// took to become audible, how deep the playback queue got, whether an
    /// interrupt really closed the mouth, whether late audio was dropped, and the
    /// frame time throughout.
    ///
    /// Without the flag it does nothing at all, so a normal run is unchanged.
    ///
    /// What it does not do: it never touches the microphone, and with the service
    /// running a stub ASR and a stub LLM the reply text is canned. The TTS, the
    /// resampling, the mixer and the lip sync are real. Results from it are
    /// desktop-measured, never headset-measured - see docs/acceptance.md.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SiSelfTest : MonoBehaviour
    {
        public const string FlagName = "-mgfr-selftest";

        // ---- configuration ---------------------------------------------------

        string _reportPath = "";
        string _url = DialogueClient.DefaultUrl;
        string _prompt = "你好，请用一句话介绍你自己。";
        float _totalSeconds = 120f;
        float _gapSeconds = 3f;
        int _rounds;
        bool _interrupt;
        float _interruptAfter = 1.2f;
        bool _reconnect;

        // ---- resolved scene objects ------------------------------------------

        DialogueClient _client;
        SiCharacterController _controller;
        SiCharacterLoader _loader;

        // ---- recorded evidence -----------------------------------------------

        readonly List<string> _log = new List<string>();
        readonly List<string> _samples = new List<string>();
        readonly List<string> _failures = new List<string>();
        readonly List<string> _errors = new List<string>();

        string _lastError = "";
        bool _replyDone;
        string _asrText = "";

        float _startTime;
        float _sampleAccum;
        int _sampleFrames;
        float _sampleWorst;
        int _blinkSamples;
        int _mouthSamples;
        int _sampleCount;
        int _blinkCount;
        bool _blinkWasOpen;

        int _promptsSent;
        int _repliesCompleted;
        int _repliesInterrupted;
        int _timeouts;
        float _firstAudibleWorst;
        int _maxQueued;
        long _maxDroppedSamples;
        int _maxDroppedFrames;
        bool _waitOk;

        // ---- bootstrap -------------------------------------------------------

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Bootstrap()
        {
            var args = Environment.GetCommandLineArgs();
            if (!HasFlag(args, FlagName))
                return;

            if (FindAnyObjectByType<SiSelfTest>() != null)
                return;

            var go = new GameObject("MGFR Self Test");
            DontDestroyOnLoad(go);
            var test = go.AddComponent<SiSelfTest>();
            test.Configure(args);
        }

        void Configure(string[] args)
        {
            _reportPath = StringArg(args, "-mgfr-report",
                Path.Combine(Application.persistentDataPath, "mgfr-selftest.txt"));
            _url = StringArg(args, "-mgfr-url", _url);
            _prompt = StringArg(args, "-mgfr-prompt", _prompt);
            _totalSeconds = FloatArg(args, "-mgfr-seconds", _totalSeconds);
            _gapSeconds = FloatArg(args, "-mgfr-gap", _gapSeconds);
            _rounds = IntArg(args, "-mgfr-rounds", 0);
            _interruptAfter = FloatArg(args, "-mgfr-interrupt-after", _interruptAfter);
            _interrupt = HasFlag(args, "-mgfr-interrupt");
            _reconnect = HasFlag(args, "-mgfr-reconnect");
        }

        // ---- lifecycle -------------------------------------------------------

        void Start()
        {
            StartCoroutine(Sample());
            StartCoroutine(Run());
        }

        void Resolve()
        {
            if (_client == null)
            {
                _client = FindAnyObjectByType<DialogueClient>();
                if (_client != null)
                {
                    _client.ReplyDone += OnReplyDone;
                    _client.AsrFinal += OnAsrFinal;
                }
            }

            if (_controller == null)
                _controller = FindAnyObjectByType<SiCharacterController>();

            if (_loader == null)
                _loader = FindAnyObjectByType<SiCharacterLoader>();
        }

        void OnReplyDone() => _replyDone = true;

        void OnAsrFinal(string text) => _asrText = text;

        // ---- the run ---------------------------------------------------------

        IEnumerator Run()
        {
            _startTime = Time.realtimeSinceStartup;

            Record("MGFR self test");
            Record($"  started        : {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
            Record($"  unity          : {Application.unityVersion}  ({Application.platform})");
            Record($"  product        : {Application.productName}");
            Record($"  graphics       : {SystemInfo.graphicsDeviceType} / {SystemInfo.graphicsDeviceName}");
            Record($"  reported vram  : {SystemInfo.graphicsMemorySize} MB");
            Record($"  colour space   : {QualitySettings.activeColorSpace}");
            Record($"  audio output   : {AudioSettings.outputSampleRate} Hz, {AudioSettings.speakerMode}");
            Record($"  xr device      : {(XRSettings.isDeviceActive ? "ACTIVE - " + XRSettings.loadedDeviceName : "none (desktop preview)")}");
            Record($"  xr suppressed  : {XrDeviceFollower.Suppressed} " +
                   $"({XrDeviceFollower.NoXrFlag} {(XrDeviceFollower.Suppressed ? "was given" : "was not given")})");
            Record($"  service url    : {_url}");
            Record($"  plan           : {_totalSeconds:0}s, " +
                   (_rounds > 0 ? $"{_rounds} rounds" : "until the clock runs out") +
                   $", interrupt={_interrupt}, reconnect={_reconnect}");
            Flush();

            var deadline = Time.realtimeSinceStartup + 30f;
            while (Time.realtimeSinceStartup < deadline)
            {
                Resolve();
                if (_client != null && _controller != null && _loader != null)
                    break;
                yield return null;
            }

            if (_client == null) { Fail("no DialogueClient appeared in the scene"); yield break; }
            if (_controller == null) { Fail("no SiCharacterController appeared in the scene"); yield break; }

            Record($"  model          : {(_loader != null ? _loader.Status : "(no SiCharacterLoader in the scene)")}");
            if (_loader != null && _loader.IsReady)
            {
                Record($"  blend shapes   : {_loader.BlendShapeCount} on the mesh, " +
                       $"blink index {_loader.FindBlendShape("まばたき")}, vowel あ index {_loader.FindBlendShape("あ")}");
            }

            Record("");
            Record("-- connect --");
            _client.Connect(_url);
            yield return StartCoroutine(WaitFor(() => _client.State == DialogueState.Connected, 15f, "the socket to connect"));
            if (!_waitOk) { Fail($"connect failed: {_client.State} / {_client.LastError}"); yield break; }

            // hello.ack comes back on the same socket, so it can land a frame or two
            // after the socket reports itself connected. Recording the version and
            // the declared rate before it arrives writes "0 Hz x0" into the report
            // and makes a working handshake look like a broken one. This wait is
            // soft: a missing ack is not a failure here, because every round after
            // this records the same two figures again.
            yield return StartCoroutine(WaitSoft(() => !string.IsNullOrEmpty(_client.ServerVersion), 5f));

            Record($"  connected      : {_client.StatusLine}");
            Record($"  server version : {_client.ServerVersion}");
            Record($"  declared tts   : {_client.TtsSampleRate} Hz x{_client.TtsChannels}");
            Flush();

            _client.StartSession();
            yield return StartCoroutine(WaitFor(() => _client.ServerState == "listening", 10f, "the session to start"));
            if (!_waitOk) { Fail($"session.start did not reach listening: {_client.ServerState} / {_client.LastError}"); yield break; }

            Record($"  session        : listening, round {_client.CurrentRound}");
            Flush();

            var round = 0;
            while (Time.realtimeSinceStartup - _startTime < _totalSeconds)
            {
                if (_rounds > 0 && round >= _rounds)
                    break;

                round++;
                yield return StartCoroutine(OneRound(round, _interrupt && round % 2 == 0, _reconnect && round == 2));
            }

            Record("");
            Record("-- end --");
            _client.EndSession();
            yield return new WaitForSecondsRealtime(0.5f);
            _client.Disconnect();
            yield return new WaitForSecondsRealtime(0.5f);
            Record($"  final state    : {_client.State}");

            Summarise();
            Flush();
            Quit(_failures.Count == 0 && _timeouts == 0 ? 0 : 1);
        }

        IEnumerator OneRound(int index, bool interrupt, bool reconnect)
        {
            Record("");
            Record($"-- round {index} --");

            if (reconnect)
            {
                Record("  reconnect test: dropping the socket mid-session");
                _client.Disconnect();
                yield return new WaitForSecondsRealtime(0.5f);

                var levelWhileDown = _client.CurrentLevel;
                var roundWhileDown = _client.CurrentRound;
                Record($"  while down     : state {_client.State}, round {roundWhileDown}, " +
                       $"level {levelWhileDown:0.000}, speaking {_client.IsSpeaking}");
                if (levelWhileDown > 0.0005f)
                    Record("  PROBLEM: audio was still audible after the socket dropped");
                if (roundWhileDown != 0)
                    Record($"  PROBLEM: the round was not reset on disconnect ({roundWhileDown})");

                _client.Connect(_url);
                yield return StartCoroutine(WaitFor(() => _client.State == DialogueState.Connected, 15f, "the reconnect"));
                if (!_waitOk) { Fail($"reconnect failed: {_client.LastError}"); yield break; }

                _client.StartSession();
                yield return StartCoroutine(WaitFor(() => _client.ServerState == "listening", 10f, "the new session"));
                if (!_waitOk) { Fail("the new session did not start"); yield break; }

                Record($"  reconnected    : round {_client.CurrentRound}, " +
                       $"dropped frames so far {_client.DroppedAudioFrames}");
            }

            Record($"  prompt         : {_prompt}");

            _replyDone = false;
            _asrText = "";
            var framesBefore = _client.DroppedAudioFrames;
            var droppedBefore = _client.DroppedSamples;
            _promptsSent++;

            var sentAt = Time.realtimeSinceStartup;
            _client.SendTextPrompt(_prompt);

            yield return StartCoroutine(WaitFor(() => _client.IsSpeaking, 60f, "the reply to become audible"));
            if (!_waitOk)
            {
                Fail($"no audible reply in round {index}: state {_client.State}, " +
                     $"server {_client.ServerState}, error {_client.LastError}");
                yield break;
            }

            var firstAudible = Time.realtimeSinceStartup - sentAt;
            if (firstAudible > _firstAudibleWorst)
                _firstAudibleWorst = firstAudible;

            Record($"  audible after  : {firstAudible:0.00}s");
            Record($"  asr            : {Trunc(_asrText, 60)}");
            Record($"  reply          : {Trunc(_client.ReplyText, 80)}");
            Record($"  tts declared   : {_client.TtsSampleRate} Hz x{_client.TtsChannels}");

            if (interrupt)
            {
                var speakStart = Time.realtimeSinceStartup;
                yield return StartCoroutine(WaitFor(
                    () => Time.realtimeSinceStartup - speakStart >= _interruptAfter,
                    _interruptAfter + 1f, "the interrupt delay"));

                Record($"  interrupting   : after {Time.realtimeSinceStartup - speakStart:0.00}s of speech");
                _client.Interrupt();

                yield return StartCoroutine(WaitFor(() => !_client.IsSpeaking, 3f, "the mouth to close"));
                Record($"  mouth closed   : {(_waitOk ? $"{Time.realtimeSinceStartup - speakStart - _interruptAfter:0.00}s after the interrupt" : "DID NOT CLOSE")}");

                yield return StartCoroutine(WaitFor(() => _client.QueuedSamples == 0, 3f, "the queue to drain"));
                Record($"  queue drained  : {(_waitOk ? "yes" : "NO - " + _client.QueuedSamples + " samples left")}");
                Record($"  late audio     : {_client.DroppedAudioFrames - framesBefore} frames / " +
                       $"{_client.DroppedSamples - droppedBefore} samples discarded");
                _repliesInterrupted++;
            }
            else
            {
                yield return StartCoroutine(WaitFor(
                    () => _replyDone && !_client.IsSpeaking && _client.QueuedSamples == 0,
                    120f, "the reply to finish playing"));

                Record($"  finished       : {(_waitOk ? $"in {Time.realtimeSinceStartup - sentAt:0.00}s" : "TIMEOUT - still playing or the queue never drained")}");
                Record($"  queue at end   : {_client.QueuedSamples} samples, {_client.DroppedSamples} dropped in total");
                Record($"  finish reason  : {_client.FinishReason}");
                if (_waitOk)
                    _repliesCompleted++;
            }

            Flush();
            yield return new WaitForSecondsRealtime(_gapSeconds);
        }

        // ---- per-second sampling --------------------------------------------

        IEnumerator Sample()
        {
            var next = Time.realtimeSinceStartup + 1f;

            while (true)
            {
                _sampleAccum += Time.unscaledDeltaTime;
                _sampleFrames++;
                if (Time.unscaledDeltaTime > _sampleWorst)
                    _sampleWorst = Time.unscaledDeltaTime;

                // Blink edges are counted every frame, not once a second. A blink
                // lasts blinkDuration - 0.13 s by default - and repeats every few
                // seconds, so a once-a-second look lands inside one roughly three
                // times in a hundred. A run whose blink works perfectly still
                // reports "no blink" at that rate, which reads like a failure. The
                // rising edge is the measurement that answers "did she blink".
                var blinkNow = _controller != null ? _controller.Blink : 0f;
                if (blinkNow > 0.01f)
                {
                    if (!_blinkWasOpen)
                    {
                        _blinkWasOpen = true;
                        _blinkCount++;
                    }
                }
                else
                {
                    _blinkWasOpen = false;
                }

                if (Time.realtimeSinceStartup >= next)
                {
                    next += 1f;

                    var avgMs = _sampleFrames > 0 ? _sampleAccum / _sampleFrames * 1000f : 0f;
                    var worstMs = _sampleWorst * 1000f;
                    var elapsed = Time.realtimeSinceStartup - _startTime;

                    var queued = _client != null ? _client.QueuedSamples : 0;
                    var dropped = _client != null ? _client.DroppedSamples : 0L;
                    var frames = _client != null ? _client.DroppedAudioFrames : 0;
                    var mouth = _controller != null ? _controller.MouthOpen : 0f;
                    var blink = _controller != null ? _controller.Blink : 0f;

                    if (queued > _maxQueued) _maxQueued = queued;
                    if (dropped > _maxDroppedSamples) _maxDroppedSamples = dropped;
                    if (frames > _maxDroppedFrames) _maxDroppedFrames = frames;
                    if (blink > 0.01f) _blinkSamples++;
                    if (mouth > 0.01f) _mouthSamples++;
                    _sampleCount++;

                    if (_client != null && !string.IsNullOrEmpty(_client.LastError) && _client.LastError != _lastError)
                    {
                        _lastError = _client.LastError;
                        _errors.Add(_lastError);
                        Record($"  error at t+{elapsed:0}s: {_lastError}");
                    }

                    _samples.Add(string.Format(CultureInfo.InvariantCulture,
                        "  t+{0,4:0}s  fps {1,5:0.0}  frame {2,5:0.00}ms  worst {3,6:0.00}ms  " +
                        "srv {4,-11}  rnd {5,3}  speak {6,-3}  level {7:0.000}  mouth {8:0.00}  blink {9:0.00}  " +
                        "queued {10,6}  drop {11,4}f/{12,7}s  vram {13} MB",
                        elapsed,
                        _sampleFrames / Mathf.Max(0.0001f, _sampleAccum),
                        avgMs, worstMs,
                        _client != null ? _client.ServerState : "-",
                        _client != null ? _client.CurrentRound : 0,
                        _client != null && _client.IsSpeaking ? "yes" : "no",
                        _client != null ? _client.CurrentLevel : 0f,
                        mouth, blink, queued, frames, dropped, GraphicsMemoryMb()));

                    _sampleAccum = 0f;
                    _sampleFrames = 0;
                    _sampleWorst = 0f;

                    if (_sampleCount % 15 == 0)
                        Flush();
                }

                yield return null;
            }
        }

        // ---- waiting ---------------------------------------------------------

        /// <summary>
        /// Waits for a condition without counting a miss against the result.
        ///
        /// <see cref="WaitFor"/> is for things that must happen, and a miss there is
        /// a failure. Some waits only exist to let an asynchronous report catch up,
        /// and a miss is recorded by whatever reads the value afterwards instead.
        /// Those use this one, so a slow ack cannot turn a passing run into a
        /// failing one.
        /// </summary>
        IEnumerator WaitSoft(Func<bool> condition, float timeout)
        {
            var deadline = Time.realtimeSinceStartup + timeout;
            while (!condition() && Time.realtimeSinceStartup < deadline)
                yield return null;
        }

        IEnumerator WaitFor(Func<bool> condition, float timeout, string what)
        {
            _waitOk = condition();
            var deadline = Time.realtimeSinceStartup + timeout;

            while (!_waitOk && Time.realtimeSinceStartup < deadline)
            {
                yield return null;
                _waitOk = condition();
            }

            if (!_waitOk)
            {
                _timeouts++;
                Record($"  TIMEOUT: {what} (gave up after {timeout:0}s)");
            }
        }

        // ---- reporting -------------------------------------------------------

        void Record(string line)
        {
            _log.Add(line);
            Debug.Log("[selftest] " + line);
        }

        void Fail(string reason)
        {
            _failures.Add(reason);
            Record($"  FAIL: {reason}");
            Summarise();
            Flush();
            Quit(1);
        }

        void Summarise()
        {
            Record("");
            Record("-- summary --");
            Record($"  prompts sent        : {_promptsSent}");
            Record($"  replies completed   : {_repliesCompleted}");
            Record($"  replies interrupted : {_repliesInterrupted}");
            Record($"  wait timeouts       : {_timeouts}");
            Record($"  worst time to audio : {_firstAudibleWorst:0.00}s");
            Record($"  deepest queue       : {_maxQueued} samples ({_maxQueued / 48000.0 / 2.0:0.00}s of stereo)");
            Record($"  most dropped        : {_maxDroppedSamples} samples, {_maxDroppedFrames} frames");
            Record($"  seconds sampled     : {_sampleCount} ({_blinkSamples} with a blink, {_mouthSamples} with the mouth open)");
            Record($"  blinks observed     : {_blinkCount} (per frame; the per-second look above misses most of them)");
            Record($"  final service state : {(_client != null ? _client.State.ToString() : "-")}");
            Record($"  final server state  : {(_client != null ? _client.ServerState : "-")}");
            Record($"  errors seen         : {_errors.Count}");
            foreach (var e in _errors)
                Record($"    ! {e}");
            Record(_failures.Count == 0 && _timeouts == 0
                ? "RESULT: pass"
                : "RESULT: incomplete - see the FAIL and TIMEOUT lines above");
        }

        void Flush()
        {
            if (string.IsNullOrEmpty(_reportPath))
                return;

            try
            {
                var dir = Path.GetDirectoryName(_reportPath);
                if (!string.IsNullOrEmpty(dir))
                    Directory.CreateDirectory(dir);

                var sb = new StringBuilder();
                foreach (var line in _log)
                    sb.AppendLine(line);
                sb.AppendLine();
                sb.AppendLine("-- per-second samples --");
                foreach (var line in _samples)
                    sb.AppendLine(line);

                File.WriteAllText(_reportPath, sb.ToString(), new UTF8Encoding(false));
            }
            catch (Exception e)
            {
                Debug.LogWarning("[selftest] could not write the report to " + _reportPath + ": " + e.Message);
            }
        }

        // ---- helpers ---------------------------------------------------------

        static long GraphicsMemoryMb()
        {
            try { return Profiler.GetAllocatedMemoryForGraphicsDriver() / (1024 * 1024); }
            catch { return -1; }
        }

        static string Trunc(string text, int max)
        {
            if (string.IsNullOrEmpty(text))
                return "(none)";
            return text.Length <= max ? text : text.Substring(0, max) + "...";
        }

        static void Quit(int code)
        {
#if UNITY_EDITOR
            UnityEditor.EditorApplication.isPlaying = false;
#else
            Application.Quit(code);
#endif
        }

        static bool HasFlag(string[] args, string flag)
        {
            foreach (var a in args)
                if (string.Equals(a, flag, StringComparison.OrdinalIgnoreCase))
                    return true;
            return false;
        }

        static string StringArg(string[] args, string name, string fallback)
        {
            for (var i = 0; i < args.Length - 1; i++)
                if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase))
                    return args[i + 1];
            return fallback;
        }

        static float FloatArg(string[] args, string name, float fallback)
        {
            return float.TryParse(StringArg(args, name, null), NumberStyles.Float,
                CultureInfo.InvariantCulture, out var value) ? value : fallback;
        }

        static int IntArg(string[] args, string name, int fallback)
        {
            return int.TryParse(StringArg(args, name, null), NumberStyles.Integer,
                CultureInfo.InvariantCulture, out var value) ? value : fallback;
        }
    }
}
