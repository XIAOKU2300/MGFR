using System;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace MGFR.Dialogue
{
    /// <summary>
    /// Connection-level state. This is deliberately separate from the server's own
    /// dialogue state (idle / listening / thinking / speaking), which arrives in
    /// <c>state</c> messages and is exposed as <see cref="DialogueClient.ServerState"/>.
    /// A single enum for both would conflate "the socket is down" with "the model
    /// is thinking", and the HUD needs to tell those apart.
    /// </summary>
    public enum DialogueState
    {
        Disconnected,
        Connecting,
        Connected,
        Failed,
    }

    /// <summary>
    /// Owns one <see cref="WebSocketConnection"/> and turns the dialogue protocol
    /// into something the rest of the game can read.
    ///
    /// Everything here runs on the main thread. The socket thread only parses bytes
    /// and pushes whole messages onto a queue; <see cref="Update"/> drains that
    /// queue. That is deliberate: handling messages on the socket thread would mean
    /// every field the HUD reads needs its own lock, and the audio thread would be
    /// racing the network thread for the ring buffer.
    ///
    /// The round number is the only turn identifier the protocol has. The server
    /// allocates it and, importantly, does not withhold audio from a cancelled
    /// round, so the client must drop any audio whose round is not the current one.
    /// That is what <see cref="DroppedAudioFrames"/> counts, and why a barge-in is
    /// handled by moving the current round forward rather than by waiting for the
    /// server to stop sending.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class DialogueClient : MonoBehaviour
    {
        /// <summary>The service's default endpoint.</summary>
        public const string DefaultUrl = "ws://127.0.0.1:8772/ws";

        // Sent in hello so the server can log which client build is talking to it.
        const string ClientVersion = "mgfr-unity-1";

        // <BBHIQIHH>: version, kind, flags, round, seq, sample_rate, channels, frame_ms.
        const int HeaderSize = 24;

        // The mic is not wired up yet, but hello requires these fields. They are
        // the values the service's own defaults use.
        const int MicSampleRate = 16000;
        const int MicChannels = 1;

        static readonly DateTime UnixEpoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        [SerializeField] DialogueAudioOutput _audio;

        WebSocketConnection _socket;

        DialogueState _state = DialogueState.Disconnected;
        string _lastError = "";

        // Current round, as the client believes it. Written from `state` messages
        // (authoritative) and moved forward on any interrupt. See HandleBargeIn.
        int _currentRound;

        // Round whose playback has been announced, or -1 when nothing is playing.
        int _playbackStartedRound = -1;

        // Set when the model has finished producing text. Playback is only declared
        // finished once this is set *and* the queue has drained, so an inter-sentence
        // gap does not look like the end of the turn.
        bool _replyComplete;bool _audioTransportComplete;int _streamAudioRound=-1;long streamAcceptedStart,streamPlayedStart,streamDroppedStart;int streamUnderrunStart;

        int _droppedAudioFrames;
        int _pingCounter;

        string _lastAsrText = "";
        string _replyText = "";
        string _finishReason = "";
        string _serverState = "";
        string _serverDetail = "";
        string _serverVersion = "";
        int _ttsSampleRate;
        int _ttsChannels;
        int _lastPongT;

        // ---- DTOs -----------------------------------------------------------
        //
        // JsonUtility needs concrete [Serializable] classes; it cannot read into a
        // Dictionary, and it silently ignores fields it does not know. That is
        // exactly the behaviour wanted here: the server may add fields and this
        // client keeps working.

        [Serializable]
        sealed class AudioInfo
        {
            // hello.ack names the TTS format ttsSampleRate / ttsChannels.
            public int ttsSampleRate;
            public int ttsChannels;

            // tts.start names the same things sampleRate / channels.
            public int sampleRate;
            public int channels;

            public string sampleFormat;
            public string container;
        }

        [Serializable]
        sealed class EnginesInfo
        {
            public string vad;
            public string asr;
            public string llm;
            public string tts;
        }

        [Serializable]
        sealed class LimitsInfo
        {
            public int maxConcurrentTts;
        }

        [Serializable]
        sealed class ControlMessage
        {
            public int v;
            public string type;
            public double ts;
            public int round;
            public string text;
            public string state;
            public string detail;
            public string finishReason;
            public int sentenceIndex;
            public string reason;
            public string code;
            public string message;
            public bool recoverable;
            public string serverVersion;
            public AudioInfo audio;
            public EnginesInfo engines;
            public LimitsInfo limits;
            public int t;
        }

        // ---- public surface -------------------------------------------------

        /// <summary>Connection state, not the server's dialogue state.</summary>
        public DialogueState State => _state;

        /// <summary>One line describing the connection, preferring the failure reason.</summary>
        public string StatusLine
        {
            get
            {
                if (_socket == null)
                    return _state.ToString();

                if (!string.IsNullOrEmpty(_socket.LastError))
                    return _socket.LastError;

                return string.IsNullOrEmpty(_socket.StatusLine) ? _state.ToString() : _socket.StatusLine;
            }
        }

        /// <summary>Last protocol or socket error, or empty.</summary>
        public string LastError
        {
            get
            {
                if (!string.IsNullOrEmpty(_lastError))
                    return _lastError;

                return _socket != null ? _socket.LastError : "";
            }
        }

        /// <summary>Server-allocated turn identifier, or 0 when no turn is active.</summary>
        public int CurrentRound => _currentRound;

        /// <summary>Text of the most recent final ASR result.</summary>
        public string LastAsrText => _lastAsrText;

        /// <summary>Reply text accumulated from llm.delta messages.</summary>
        public string ReplyText => _replyText;

        /// <summary>
        /// True while audio is actually being played. This is the mouth-open signal
        /// for an avatar, so it tracks the mixer, not the server's intent.
        /// </summary>
        public bool IsSpeaking => _audio != null && _audio.IsAudible;
        public bool SendMicrophoneFrame(byte[] frame) => _socket != null && _socket.IsOpen && _socket.SendBinary(frame);

        /// <summary>Audio frames discarded because their round was not current.</summary>
        public int DroppedAudioFrames => _droppedAudioFrames;

        /// <summary>The server's dialogue state: idle, listening, recognizing, thinking, speaking, error.</summary>
        public string ServerState => _serverState;

        /// <summary>Optional detail that accompanies <see cref="ServerState"/>.</summary>
        public string ServerDetail => _serverDetail;

        /// <summary>Version string the server reported in hello.ack.</summary>
        public string ServerVersion => _serverVersion;

        /// <summary>TTS sample rate the server reported. May be 0, which means "unknown".</summary>
        public int TtsSampleRate => _ttsSampleRate;

        /// <summary>TTS channel count the server reported. May be 0.</summary>
        public int TtsChannels => _ttsChannels;

        /// <summary>Why the last llm.done arrived: completed, interrupted or error.</summary>
        public string FinishReason => _finishReason;

        /// <summary>The last t value echoed by the server in a pong.</summary>
        public int LastPongT => _lastPongT;

        /// <summary>Samples queued for playback but not yet played.</summary>
        public int QueuedSamples => _audio != null ? _audio.QueuedSamples : 0;

        /// <summary>Samples the audio ring had to discard because it was full.</summary>
        public long DroppedSamples => _audio != null ? _audio.DroppedSamples : 0;

        /// <summary>Output level of the last mixer callback, 0..1.</summary>
        public float CurrentLevel => _audio != null ? _audio.CurrentLevel : 0f;

        /// <summary>Raised on the main thread when a final ASR result arrives.</summary>
        public event Action<string> AsrFinal;

        /// <summary>Raised on the main thread for each reply text fragment.</summary>
        public event Action<string> ReplyDelta;

        /// <summary>Raised on the main thread when the reply stream ends.</summary>
        public event Action ReplyDone;
        public event Action<int,int,string,long> SentenceQueued;

        // ---- lifecycle ------------------------------------------------------

        void Awake()
        {
            if (_audio == null)
                _audio = GetComponent<DialogueAudioOutput>();

            // The client is useless without an output, and requiring the caller to
            // wire one up by hand is a footgun, so it is added on demand.
            if (_audio == null)
                _audio = gameObject.AddComponent<DialogueAudioOutput>();
        }

        void Update()
        {
            try
            {
                PollSocket();
                PumpPlayback();
            }
            catch (Exception e)
            {
                // Nothing may escape Update: a throw here would stop every other
                // Update in the scene and leave the socket thread orphaned.
                _lastError = e.GetType().Name + ": " + e.Message;
            }
        }

        void OnDestroy()
        {
            Disconnect();
        }

        /// <summary>Opens a connection, replacing any existing one.</summary>
        public void Connect(string url = DefaultUrl)
        {
            if (string.IsNullOrWhiteSpace(url) || url == DefaultUrl)
            {
                var args = Environment.GetCommandLineArgs();
                int endpoint = Array.IndexOf(args, "-mgfr-service-url");
                url = endpoint >= 0 && endpoint + 1 < args.Length ? args[endpoint + 1] : DefaultUrl;
            }

            if (_socket == null)
                _socket = new WebSocketConnection();
            else
                _socket.Close();

            ResetForNewConnection();
            _lastError = "";
            _state = DialogueState.Connecting;
            _socket.Connect(url);
        }

        /// <summary>Closes the connection and returns to a clean, disconnected state.</summary>
        public void Disconnect()
        {
            if (_socket != null)
                _socket.Close();

            ResetForNewConnection();
            _state = DialogueState.Disconnected;
        }

        /// <summary>Tells the server to begin a session. Safe to call when not connected.</summary>
        public void StartSession()
        {
            if (!RequireOpen("session.start"))
                return;

            // A fresh session starts a fresh turn; anything still queued belongs to
            // the previous one.
            StopPlayback();
            _currentRound = 0;
            _replyComplete = false;
            _lastAsrText = "";
            _replyText = "";

            var sb = Begin("session.start");
            sb.Append('}');
            SendControl(sb.ToString(), "session.start");
        }

        /// <summary>Tells the server to end the session.</summary>
        public void EndSession()
        {
            if (!RequireOpen("session.end"))
                return;

            var sb = Begin("session.end");
            sb.Append('}');
            SendControl(sb.ToString(), "session.end");

            // The server answers with state(0, idle). Clearing locally first means
            // late audio from the ending round is dropped immediately rather than
            // during the round trip.
            StopPlayback();
            _currentRound = 0;
            _replyComplete = false;
        }

        /// <summary>Asks the server to abandon the current turn.</summary>
        public void Interrupt()
        {
            if (!RequireOpen("interrupt"))
                return;

            var sb = Begin("interrupt");
            sb.Append(",\"source\":");
            AppendString(sb, "client");
            sb.Append('}');
            SendControl(sb.ToString(), "interrupt");

            // Move past the round being interrupted now, so frames the server has
            // already put on the wire are dropped on arrival.
            HandleBargeIn(_currentRound);
        }

        /// <summary>Sends an application-level ping. The server echoes <c>t</c> in a pong.</summary>
        public void SendPing()
        {
            if (!RequireOpen("ping"))
                return;

            _pingCounter++;
            var sb = Begin("ping");
            sb.Append(",\"t\":");
            sb.Append(_pingCounter.ToString(CultureInfo.InvariantCulture));
            sb.Append('}');
            SendControl(sb.ToString(), "ping");
        }

        /// <summary>
        /// Sends a typed line as if it had been spoken. A server that does not know
        /// <c>text.input</c> logs and ignores it, so this is safe against an older
        /// service.
        /// </summary>
        public void SendTextPrompt(string text)
        {
            if (string.IsNullOrEmpty(text))
                return;

            if (!RequireOpen("text.input"))
                return;

            var sb = Begin("text.input");
            sb.Append(",\"text\":");
            AppendString(sb, text);
            sb.Append('}');
            SendControl(sb.ToString(), "text.input");
        }

        // ---- polling --------------------------------------------------------

        void PollSocket()
        {
            if (_socket == null)
                return;

            // A connected socket that has gone away is noticed before draining, so
            // messages already queued by a dead socket are not acted on.
            if (_state == DialogueState.Connected && !_socket.IsOpen)
            {
                _state = DialogueState.Disconnected;
                ResetForNewConnection();
                DrainSocket();
                return;
            }

            DrainSocket();

            if (_state == DialogueState.Connecting)
            {
                if (_socket.IsOpen)
                {
                    _state = DialogueState.Connected;
                    SendHello();
                }
                else if (!string.IsNullOrEmpty(_socket.LastError))
                {
                    _state = DialogueState.Failed;
                    _lastError = _socket.LastError;
                }
            }
        }

        void DrainSocket()
        {
            int drained=0;long started=System.Diagnostics.Stopwatch.GetTimestamp();
            while (_socket.TryPeekMessage(out WebSocketMessage message))
            {
                if(WaitForAudioSpace(message))break;
                _socket.TryDequeueMessage(out message);
                if (message.Kind == WebSocketMessageKind.Text)
                    HandleText(message.Text);
                else
                    HandleBinary(message.Binary);
                if(++drained>=64||(System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000d/System.Diagnostics.Stopwatch.Frequency>1.5)break;
            }
        }
        bool WaitForAudioSpace(WebSocketMessage message)
        {
            var data=message.Binary;
            if(_audio==null||message.Kind!=WebSocketMessageKind.Binary||data==null||data.Length<HeaderSize||data[0]!=1||data[1]!=2||ReadUInt32(data,4)!=(uint)_currentRound)return false;
            return !_audio.CanAccept(data.Length-HeaderSize,ReadUInt16(data,20),(int)ReadUInt32(data,16));
        }

        /// <summary>
        /// Declares playback finished once the model is done and the queue has
        /// drained. Gating on <see cref="_replyComplete"/> matters: without it, the
        /// silence between two spoken sentences would be reported as the end of the
        /// turn, which is wrong and would confuse the server's echo suppression.
        /// </summary>
        void PumpPlayback()
        {
            if (_audio == null)
                return;
            if (_playbackStartedRound < 0 || _playbackStartedRound != _currentRound)
                return;
            if (!_replyComplete || !_audioTransportComplete)
                return;
            if (_audio.IsAudible || _audio.QueuedSamples > 0)
                return;

            Debug.Log($"[MGFR stream] round={_currentRound} accepted={_audio.AcceptedSamples-streamAcceptedStart} played={_audio.PlayedSamples-streamPlayedStart} dropped={_audio.DroppedSamples-streamDroppedStart} underruns={_audio.UnderrunEvents-streamUnderrunStart} dspFrames={_audio.MaxCallbackFrames}");
            SendPlaybackFinished(_currentRound);
            _playbackStartedRound = -1;
        }

        // ---- incoming text --------------------------------------------------

        void HandleText(string json)
        {
            if (string.IsNullOrEmpty(json))
                return;

            ControlMessage m;
            try
            {
                m = JsonUtility.FromJson<ControlMessage>(json);
            }
            catch (Exception e)
            {
                _lastError = "unreadable control message: " + e.Message;
                return;
            }

            if (m == null || m.type == null)
                return;

            if (m.v != 1)
            {
                // The envelope version is a hard contract; a mismatch means the
                // server and client disagree about the protocol.
                _lastError = "protocol version " + m.v + " (expected 1)";
                return;
            }

            switch (m.type)
            {
                case "hello.ack":
                    HandleHelloAck(m);
                    break;

                case "state":
                    // state carries the authoritative round. A change of round
                    // means a new turn, so per-turn flags reset here.
                    if (m.round != _currentRound)
                    {
                        _replyComplete = false;
                        _playbackStartedRound = -1;
                    }

                    _currentRound = m.round;
                    _serverState = m.state ?? "";
                    _serverDetail = m.detail ?? "";
                    break;

                case "asr.final":
                    _lastAsrText = m.text ?? "";
                    RaiseAsrFinal(_lastAsrText);
                    break;

                case "llm.delta":
                    if (!string.IsNullOrEmpty(m.text))
                    {
                        _replyText += m.text;
                        RaiseReplyDelta(m.text);
                    }
                    break;

                case "llm.done":
                    _finishReason = m.finishReason ?? "";
                    _replyComplete = true;
                    RaiseReplyDone();
                    break;

                case "tts.start":
                    HandleTtsStart(m);
                    break;

                case "audio.done":
                    if(m.round==_currentRound){_audioTransportComplete=true;_audio.CompleteStream();}
                    break;

                case "tts.end":
                    // Nothing to do: the audio itself is what drives playback, and
                    // tts.end only marks the end of a sentence's generation.
                    break;

                case "interrupt":
                    // The server interrupts for user speech, a client request, or a
                    // session end. In every case the audio must stop now.
                    HandleBargeIn(m.round);
                    break;

                case "error":
                    _lastError = (string.IsNullOrEmpty(m.code) ? "error" : m.code) + ": " + (m.message ?? "");
                    _serverState = "error";
                    _serverDetail = m.message ?? "";
                    Debug.LogWarning("[MGFR] server error " + _lastError + (m.recoverable ? " (recoverable)" : " (not recoverable)"));
                    break;

                case "pong":
                    _lastPongT = m.t;
                    break;

                default:
                    // Unknown control types are ignored on purpose: the server is
                    // allowed to add messages this client has never heard of.
                    break;
            }
        }

        void HandleHelloAck(ControlMessage m)
        {
            _serverVersion = m.serverVersion ?? "";

            if (m.audio != null)
            {
                // ttsSampleRate may legitimately be 0 (the engine is not loaded
                // yet). That is not an error, and nothing may assume a fixed rate;
                // the real rate is taken from the audio frame headers instead.
                _ttsSampleRate = m.audio.ttsSampleRate;
                _ttsChannels = m.audio.ttsChannels;
            }

            Debug.Log("[MGFR] hello.ack from server " + _serverVersion +
                      ", tts " + _ttsSampleRate + " Hz x" + _ttsChannels);
        }

        void HandleTtsStart(ControlMessage m)
        {
            if(m.round==_currentRound&&_audio!=null)
                SentenceQueued?.Invoke(m.round,m.sentenceIndex,m.text??"",_audio.WriteCursor);
            if (m.audio != null)
            {
                if (m.audio.sampleRate > 0)
                    _ttsSampleRate = m.audio.sampleRate;
                if (m.audio.channels > 0)
                    _ttsChannels = m.audio.channels;
            }
        }

        // ---- incoming binary ------------------------------------------------

        void HandleBinary(byte[] data)
        {
            if (data == null || data.Length < HeaderSize)
            {
                _droppedAudioFrames++;
                return;
            }

            byte version = data[0];
            byte kind = data[1];
            uint round = ReadUInt32(data, 4);
            uint sampleRate = ReadUInt32(data, 16);
            ushort channels = ReadUInt16(data, 20);

            // Only version 1 TTS frames are understood. A mic frame (kind 1) is
            // never sent to a client, so seeing one means something is wrong.
            if (version != 1 || kind != 2)
            {
                _droppedAudioFrames++;
                return;
            }

            int frameRound = round > int.MaxValue ? int.MaxValue : (int)round;
            if (frameRound != _currentRound)
            {
                // Audio from a cancelled or superseded round. The server keeps
                // sending it, so dropping here is the only way to stop it playing.
                _droppedAudioFrames++;
                return;
            }

            if (_audio == null)
            {
                _droppedAudioFrames++;
                return;
            }

            // Prefer the per-frame header; fall back to what hello.ack or tts.start
            // reported. If neither is known the frame cannot be interpreted.
            int rate = sampleRate > 0 ? (int)sampleRate : _ttsSampleRate;
            int channelCount = channels > 0 ? channels : _ttsChannels;

            if (rate <= 0 || channelCount <= 0)
            {
                _droppedAudioFrames++;
                return;
            }

            if(_streamAudioRound!=_currentRound)
            {
                streamAcceptedStart=_audio.AcceptedSamples;streamPlayedStart=_audio.PlayedSamples;streamDroppedStart=_audio.DroppedSamples;streamUnderrunStart=_audio.UnderrunEvents;
                _audio.BeginStream();_streamAudioRound=_currentRound;_audioTransportComplete=false;
            }
            _audio.Enqueue(data, HeaderSize, data.Length - HeaderSize, channelCount, rate);

            if (_playbackStartedRound != _currentRound)
            {
                _playbackStartedRound = _currentRound;
                SendPlaybackStarted(_currentRound);
            }
        }

        // ---- round handling -------------------------------------------------

        /// <summary>
        /// Stops audio and moves the current round past <paramref name="messageRound"/>.
        ///
        /// The move is monotonic on purpose. A client-requested interrupt and the
        /// server's own interrupt message for it both try to advance the round, and
        /// a plain increment would advance twice. The following <c>state</c> message
        /// carries the true round and corrects anything this got wrong, which is
        /// safe because audio for a new round never precedes its state message.
        /// </summary>
        void HandleBargeIn(int messageRound)
        {
            StopPlayback();
            _replyComplete = false;

            int candidate = messageRound == int.MaxValue ? int.MaxValue : messageRound + 1;
            if (candidate > _currentRound)
                _currentRound = candidate;
        }

        void StopPlayback()
        {
            _streamAudioRound=-1;_audioTransportComplete=false;
            if (_audio != null)
                _audio.StopAndClear();

            _playbackStartedRound = -1;
        }

        void ResetForNewConnection()
        {
            StopPlayback();
            _currentRound = 0;
            _replyComplete = false;
            _droppedAudioFrames = 0;
            _lastAsrText = "";
            _replyText = "";
            _finishReason = "";
            _serverState = "";
            _serverDetail = "";
        }

        // ---- outgoing -------------------------------------------------------

        void SendHello()
        {
            var sb = Begin("hello");
            sb.Append(",\"clientVersion\":");
            AppendString(sb, ClientVersion);
            sb.Append(",\"audio\":{\"micSampleRate\":");
            sb.Append(MicSampleRate.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"micChannels\":");
            sb.Append(MicChannels.ToString(CultureInfo.InvariantCulture));
            sb.Append("},\"capabilities\":[\"text.input\"]}");
            SendControl(sb.ToString(), "hello");
        }

        void SendPlaybackStarted(int round)
        {
            var sb = Begin("playback.started");
            sb.Append(",\"round\":");
            sb.Append(round.ToString(CultureInfo.InvariantCulture));
            sb.Append('}');
            SendControl(sb.ToString(), "playback.started");
        }

        void SendPlaybackFinished(int round)
        {
            var sb = Begin("playback.finished");
            sb.Append(",\"round\":");
            sb.Append(round.ToString(CultureInfo.InvariantCulture));
            sb.Append('}');
            SendControl(sb.ToString(), "playback.finished");
        }

        bool RequireOpen(string what)
        {
            if (_socket != null && _socket.IsOpen)
                return true;

            _lastError = "cannot send " + what + ": not connected";
            return false;
        }

        bool SendControl(string json, string what)
        {
            if (_socket == null || !_socket.IsOpen)
            {
                _lastError = "cannot send " + what + ": not connected";
                return false;
            }

            if (!_socket.SendText(json))
            {
                _lastError = "send " + what + " failed: " + _socket.LastError;
                return false;
            }

            return true;
        }

        /// <summary>
        /// Starts an envelope. The service requires v == 1 and a ts on every
        /// message; ts is unix seconds, sent as an integer because the service
        /// treats it as a number it only records.
        /// </summary>
        static StringBuilder Begin(string type)
        {
            var sb = new StringBuilder(160);
            sb.Append("{\"v\":1,\"type\":");
            AppendString(sb, type);
            sb.Append(",\"ts\":");
            sb.Append(UnixSeconds().ToString(CultureInfo.InvariantCulture));
            return sb;
        }

        static long UnixSeconds()
        {
            return (long)(DateTime.UtcNow - UnixEpoch).TotalSeconds;
        }

        static void AppendString(StringBuilder sb, string value)
        {
            sb.Append('"');

            if (!string.IsNullOrEmpty(value))
            {
                for (int i = 0; i < value.Length; i++)
                {
                    char c = value[i];
                    switch (c)
                    {
                        case '"': sb.Append("\\\""); break;
                        case '\\': sb.Append("\\\\"); break;
                        case '\n': sb.Append("\\n"); break;
                        case '\r': sb.Append("\\r"); break;
                        case '\t': sb.Append("\\t"); break;
                        case '\b': sb.Append("\\b"); break;
                        case '\f': sb.Append("\\f"); break;
                        default:
                            if (c < 0x20)
                            {
                                sb.Append("\\u");
                                sb.Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                            }
                            else
                            {
                                // Non-ASCII is written as-is: the payload is UTF-8,
                                // which JSON permits and the service expects.
                                sb.Append(c);
                            }

                            break;
                    }
                }
            }

            sb.Append('"');
        }

        static ushort ReadUInt16(byte[] data, int offset)
        {
            return (ushort)(data[offset] | (data[offset + 1] << 8));
        }

        static uint ReadUInt32(byte[] data, int offset)
        {
            return (uint)(data[offset]
                          | (data[offset + 1] << 8)
                          | (data[offset + 2] << 16)
                          | (data[offset + 3] << 24));
        }

        // ---- events ---------------------------------------------------------
        //
        // Raised through helpers so a subscriber that throws cannot take the
        // client down with it: a broken listener is not worth losing the socket.

        void RaiseAsrFinal(string text)
        {
            Action<string> handler = AsrFinal;
            if (handler == null)
                return;

            try
            {
                handler(text);
            }
            catch (Exception e)
            {
                Debug.LogWarning("[MGFR] AsrFinal handler threw: " + e.GetType().Name + ": " + e.Message);
            }
        }

        void RaiseReplyDelta(string text)
        {
            Action<string> handler = ReplyDelta;
            if (handler == null)
                return;

            try
            {
                handler(text);
            }
            catch (Exception e)
            {
                Debug.LogWarning("[MGFR] ReplyDelta handler threw: " + e.GetType().Name + ": " + e.Message);
            }
        }

        void RaiseReplyDone()
        {
            Action handler = ReplyDone;
            if (handler == null)
                return;

            try
            {
                handler();
            }
            catch (Exception e)
            {
                Debug.LogWarning("[MGFR] ReplyDone handler threw: " + e.GetType().Name + ": " + e.Message);
            }
        }
    }
}
