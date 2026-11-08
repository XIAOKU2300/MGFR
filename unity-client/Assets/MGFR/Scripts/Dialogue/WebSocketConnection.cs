using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

namespace MGFR.Dialogue
{
    /// <summary>Which payload a received WebSocket message carried.</summary>
    public enum WebSocketMessageKind
    {
        Text,
        Binary,
    }

    /// <summary>
    /// One complete WebSocket message, after any fragmentation has been reassembled.
    /// </summary>
    public struct WebSocketMessage
    {
        public WebSocketMessageKind Kind;
        public string Text;
        public byte[] Binary;
    }

    /// <summary>
    /// A WebSocket client written directly on top of a TCP socket.
    ///
    /// The project deliberately owns no WebSocket package: the packages that exist
    /// either drag the Unity editor in with them (websocket-sharp) or hand the
    /// caller a Task-based API that is awkward under IL2CPP. The subset of RFC 6455
    /// the dialogue service actually uses is small, so it is implemented here
    /// instead of depended on.
    ///
    /// All socket work happens on one background thread. That thread never calls
    /// back into Unity; it only parses bytes and pushes whole messages onto a
    /// ConcurrentQueue. The main thread drains that queue. This is why the class
    /// has no events and no callbacks: anything that ran on the socket thread would
    /// have to marshal itself to the main thread anyway.
    ///
    /// Failure is reported as text (StatusLine / LastError), never as an exception:
    /// the caller is a MonoBehaviour's Update, and nothing is allowed to escape it.
    /// </summary>
    public sealed class WebSocketConnection
    {
        // The RFC 6455 magic GUID. Concatenated with the client key and SHA-1'd to
        // produce the value the server must echo in Sec-WebSocket-Accept.
        const string HandshakeGuid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11";

        // A guard, not a limit: the service caps messages around 16 MiB, so anything
        // past this is a malformed frame and must not be allowed to allocate.
        const int MaxPayloadBytes = 32 * 1024 * 1024;

        const int InitialBufferBytes = 16 * 1024;

        // How long a single wait for incoming bytes lasts before the loop rechecks
        // the close flag. Short enough that Close() feels immediate.
        const int ReceiveWaitMs = 200;

        const int DefaultConnectTimeoutMs = 5000;
        const int HandshakeReadTimeoutMs = 5000;
        const int PostHandshakeReadTimeoutMs = 60000;
        const int CloseJoinTimeoutMs = 2000;

        readonly ConcurrentQueue<WebSocketMessage> _incoming = new ConcurrentQueue<WebSocketMessage>();

        // Sends can come from the main thread (control messages) and from the read
        // thread (pong replies, close replies), so they are serialised.
        readonly object _sendLock = new object();

        TcpClient _client;
        NetworkStream _stream;
        Thread _thread;

        // Read buffer and its fill level. Only the read thread touches these.
        byte[] _buffer = new byte[InitialBufferBytes];
        int _bufferCount;

        // Reassembly state for a fragmented data message. Null when none is open.
        MemoryStream _fragment;
        int _fragmentOpcode;

        volatile bool _isOpen;
        volatile bool _closeRequested;
        volatile bool _peerClosed;
        volatile string _statusLine = "not connected";
        volatile string _lastError = "";

        /// <summary>True once the handshake has succeeded and no close has been seen.</summary>
        public bool IsOpen => _isOpen;

        /// <summary>Human-readable connection status, including the HTTP status line.</summary>
        public string StatusLine => _statusLine;

        /// <summary>Why the connection failed or ended, or empty.</summary>
        public string LastError => _lastError;

        /// <summary>True once the peer has sent a close frame.</summary>
        public bool PeerClosed => _peerClosed;

        /// <summary>Number of parsed messages not yet drained by the caller.</summary>
        public int PendingMessageCount => _incoming.Count;

        /// <summary>
        /// Takes the oldest parsed message, if any. Call from the main thread.
        /// </summary>
        public bool TryDequeueMessage(out WebSocketMessage message) => _incoming.TryDequeue(out message);
        public bool TryPeekMessage(out WebSocketMessage message) => _incoming.TryPeek(out message);

        /// <summary>
        /// Starts the handshake and the read loop on a background thread. Returns
        /// immediately; poll <see cref="IsOpen"/> and <see cref="LastError"/>.
        /// </summary>
        public void Connect(string url) => Connect(url, DefaultConnectTimeoutMs);

        /// <summary>As <see cref="Connect(string)"/> but with an explicit TCP connect timeout.</summary>
        public void Connect(string url, int connectTimeoutMs)
        {
            string host, path, parseError;
            int port;

            if (!TryParseUrl(url, out host, out port, out path, out parseError))
            {
                _lastError = parseError;
                _statusLine = parseError;
                return;
            }

            // A second Connect on a live instance replaces the first connection
            // rather than sharing it, so nothing from the old socket can surface.
            CloseInternal(joinThread: true);

            _bufferCount = 0;
            _fragment = null;
            _fragmentOpcode = 0;
            _isOpen = false;
            _closeRequested = false;
            _peerClosed = false;
            _lastError = "";
            _statusLine = "connecting to " + url;
            DrainIncoming();

            _thread = new Thread(() => ThreadMain(host, port, path, connectTimeoutMs))
            {
                IsBackground = true,
                Name = "MGFR WebSocket",
            };
            _thread.Start();
        }

        /// <summary>
        /// Requests a close and waits briefly for the read thread to stop. Safe to
        /// call from the main thread or the read thread; it never throws.
        /// </summary>
        public void Close()
        {
            _closeRequested = true;
            CloseInternal(joinThread: true);
            _isOpen = false;
            if (string.IsNullOrEmpty(_lastError) && !_peerClosed)
                _statusLine = "closed";
        }

        /// <summary>Sends a UTF-8 text frame. Returns false and records the reason on failure.</summary>
        public bool SendText(string text) => SendFrame(0x1, Encoding.UTF8.GetBytes(text ?? ""));

        /// <summary>Sends a binary frame. Returns false and records the reason on failure.</summary>
        public bool SendBinary(byte[] data) => SendFrame(0x2, data ?? Array.Empty<byte>());

        // ---- thread entry ---------------------------------------------------

        void ThreadMain(string host, int port, string path, int connectTimeoutMs)
        {
            try
            {
                string statusLine;
                if (!Handshake(host, port, path, connectTimeoutMs, out statusLine))
                    return;

                _statusLine = statusLine;
                _isOpen = true;
                ReadLoop();
            }
            catch (Exception e)
            {
                // The socket thread must never let anything escape it.
                _lastError = e.GetType().Name + ": " + e.Message;
            }
            finally
            {
                _isOpen = false;
                CloseSockets();
                if (string.IsNullOrEmpty(_lastError))
                    _statusLine = _peerClosed ? "closed by peer" : "connection ended";
            }
        }

        // ---- handshake ------------------------------------------------------

        bool Handshake(string host, int port, string path, int connectTimeoutMs, out string statusLine)
        {
            statusLine = "";

            IPAddress address;
            if (!TryResolve(host, out address))
                return false;

            try
            {
                _client = new TcpClient(address.AddressFamily) { NoDelay = true };

                IAsyncResult ar = _client.BeginConnect(address, port, null, null);
                if (!ar.AsyncWaitHandle.WaitOne(connectTimeoutMs, false))
                {
                    _lastError = "connect to " + host + ":" + port + " timed out";
                    return false;
                }

                _client.EndConnect(ar);
                _stream = _client.GetStream();
                _stream.ReadTimeout = HandshakeReadTimeoutMs;
            }
            catch (Exception e)
            {
                _lastError = "connect to " + host + ":" + port + " failed: " + e.Message;
                return false;
            }

            // A 16-byte nonce, base64'd. The server echoes SHA-1(key + GUID) so we
            // can be sure we reached a WebSocket endpoint and not some other server
            // that happens to be listening on the port.
            var keyBytes = new byte[16];
            using (var rng = RandomNumberGenerator.Create())
                rng.GetBytes(keyBytes);
            string key = Convert.ToBase64String(keyBytes);

            string hostHeader = port == 80 ? host : host + ":" + port;
            string request =
                "GET " + path + " HTTP/1.1\r\n" +
                "Host: " + hostHeader + "\r\n" +
                "Upgrade: websocket\r\n" +
                "Connection: Upgrade\r\n" +
                "Sec-WebSocket-Key: " + key + "\r\n" +
                "Sec-WebSocket-Version: 13\r\n" +
                "\r\n";

            try
            {
                byte[] requestBytes = Encoding.ASCII.GetBytes(request);
                _stream.Write(requestBytes, 0, requestBytes.Length);
                _stream.Flush();
            }
            catch (Exception e)
            {
                _lastError = "handshake write failed: " + e.Message;
                return false;
            }

            string header;
            try
            {
                header = ReadHttpHeaders();
            }
            catch (Exception e)
            {
                _lastError = "handshake read failed: " + e.Message;
                return false;
            }

            if (header == null)
            {
                _lastError = "no HTTP response to the upgrade request";
                return false;
            }

            string[] lines = header.Split(new[] { "\r\n" }, StringSplitOptions.None);
            statusLine = lines.Length > 0 ? lines[0].Trim() : "";

            if (!statusLine.Contains(" 101 "))
            {
                _lastError = "server refused the upgrade: " + statusLine;
                return false;
            }

            string accept = null;
            for (int i = 1; i < lines.Length; i++)
            {
                int colon = lines[i].IndexOf(':');
                if (colon <= 0)
                    continue;

                string name = lines[i].Substring(0, colon).Trim();
                if (string.Equals(name, "Sec-WebSocket-Accept", StringComparison.OrdinalIgnoreCase))
                {
                    accept = lines[i].Substring(colon + 1).Trim();
                    break;
                }
            }

            string expected = ComputeAccept(key);
            if (accept == null || !string.Equals(accept, expected, StringComparison.Ordinal))
            {
                _lastError = "Sec-WebSocket-Accept mismatch (got '" + (accept ?? "none") + "')";
                return false;
            }

            try
            {
                // After the handshake the read loop waits with Poll, so this timeout
                // is only a backstop against a Read that blocks unexpectedly.
                _stream.ReadTimeout = PostHandshakeReadTimeoutMs;
            }
            catch
            {
                // Not fatal: some stream implementations reject a timeout change.
            }

            return true;
        }

        /// <summary>
        /// Reads bytes one at a time until the blank line that ends the HTTP
        /// response headers. Reading a byte at a time cannot consume any frame
        /// bytes the server may have pipelined behind the headers, because
        /// NetworkStream.Read never reads past what was asked for.
        /// </summary>
        string ReadHttpHeaders()
        {
            var sb = new StringBuilder(512);
            while (true)
            {
                int b = _stream.ReadByte();
                if (b < 0)
                    return sb.Length > 0 ? sb.ToString() : null;

                sb.Append((char)b);
                int n = sb.Length;
                if (n >= 4 &&
                    sb[n - 4] == '\r' && sb[n - 3] == '\n' &&
                    sb[n - 2] == '\r' && sb[n - 1] == '\n')
                {
                    return sb.ToString();
                }

                if (n > 16384)
                    return null;
            }
        }

        static string ComputeAccept(string key)
        {
            using (var sha1 = SHA1.Create())
            {
                byte[] hash = sha1.ComputeHash(Encoding.ASCII.GetBytes(key + HandshakeGuid));
                return Convert.ToBase64String(hash);
            }
        }

        static bool TryResolve(string host, out IPAddress address)
        {
            address = null;
            if (IPAddress.TryParse(host, out address))
                return true;

            try
            {
                IPAddress[] all = Dns.GetHostAddresses(host);
                foreach (IPAddress candidate in all)
                {
                    if (candidate.AddressFamily == AddressFamily.InterNetwork)
                    {
                        address = candidate;
                        break;
                    }
                }

                if (address == null && all.Length > 0)
                    address = all[0];
            }
            catch
            {
                address = null;
            }

            return address != null;
        }

        static bool TryParseUrl(string url, out string host, out int port, out string path, out string error)
        {
            host = null;
            port = 0;
            path = "/";
            error = null;

            if (string.IsNullOrWhiteSpace(url))
            {
                error = "url is empty";
                return false;
            }

            Uri uri;
            if (!Uri.TryCreate(url, UriKind.Absolute, out uri))
            {
                error = "invalid url: " + url;
                return false;
            }

            if (!string.Equals(uri.Scheme, "ws", StringComparison.OrdinalIgnoreCase))
            {
                error = "only ws:// is supported, got scheme '" + uri.Scheme + "'";
                return false;
            }

            host = uri.Host;
            port = uri.IsDefaultPort ? 80 : uri.Port;
            path = string.IsNullOrEmpty(uri.PathAndQuery) ? "/" : uri.PathAndQuery;
            return true;
        }

        // ---- read loop ------------------------------------------------------

        void ReadLoop()
        {
            while (!_closeRequested)
            {
                try
                {
                    EnsureReadSpace();

                    Socket socket = _client != null ? _client.Client : null;
                    if (socket == null)
                        break;

                    // Poll rather than a blocking Read with a timeout: a timeout on
                    // a synchronous socket surfaces as a platform-specific exception,
                    // while Poll simply reports "nothing yet" and lets the loop
                    // recheck the close flag.
                    if (!socket.Poll(ReceiveWaitMs * 1000, SelectMode.SelectRead))
                        continue;

                    int read = _stream.Read(_buffer, _bufferCount, _buffer.Length - _bufferCount);
                    if (read <= 0)
                    {
                        _peerClosed = true;
                        break;
                    }

                    _bufferCount += read;
                    ProcessIncoming();
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (SocketException e)
                {
                    if (!_closeRequested)
                        _lastError = "socket: " + e.SocketErrorCode;
                    break;
                }
                catch (IOException e)
                {
                    if (!_closeRequested)
                        _lastError = "io: " + e.Message;
                    break;
                }
                catch (Exception e)
                {
                    if (!_closeRequested)
                        _lastError = e.GetType().Name + ": " + e.Message;
                    break;
                }
            }
        }

        void EnsureReadSpace()
        {
            if (_bufferCount < _buffer.Length)
                return;

            int cap = MaxPayloadBytes + 4096;
            int next = _buffer.Length * 2;
            if (next > cap)
                next = cap;
            if (next <= _buffer.Length)
                next = _buffer.Length + 4096;

            var bigger = new byte[next];
            Buffer.BlockCopy(_buffer, 0, bigger, 0, _bufferCount);
            _buffer = bigger;
        }

        /// <summary>
        /// Consumes as many whole frames as the buffer holds, leaving any partial
        /// frame in place for the next read.
        /// </summary>
        void ProcessIncoming()
        {
            while (true)
            {
                if (_bufferCount < 2)
                    return;

                byte b0 = _buffer[0];
                byte b1 = _buffer[1];

                bool fin = (b0 & 0x80) != 0;
                int opcode = b0 & 0x0F;
                bool masked = (b1 & 0x80) != 0;
                long length = b1 & 0x7F;
                int pos = 2;

                if (length == 126)
                {
                    if (_bufferCount < 4)
                        return;
                    length = ((long)_buffer[2] << 8) | _buffer[3];
                    pos = 4;
                }
                else if (length == 127)
                {
                    if (_bufferCount < 10)
                        return;
                    length = 0;
                    for (int i = 0; i < 8; i++)
                        length = (length << 8) | _buffer[2 + i];
                    pos = 10;
                }

                if (length < 0 || length > MaxPayloadBytes)
                {
                    Fail("frame length out of range: " + length);
                    return;
                }

                int maskPos = -1;
                if (masked)
                {
                    if (_bufferCount < pos + 4)
                        return;
                    maskPos = pos;
                    pos += 4;
                }

                long total = pos + length;
                if (_bufferCount < total)
                    return;

                int payloadStart = pos;
                int payloadLength = (int)length;

                if (opcode >= 0x8)
                {
                    // Control frames are never fragmented and never exceed 125 bytes.
                    if (!fin || payloadLength > 125)
                    {
                        Fail("invalid control frame");
                        return;
                    }

                    HandleControlFrame(opcode, payloadStart, payloadLength, maskPos);
                }
                else
                {
                    HandleDataFrame(fin, opcode, payloadStart, payloadLength, maskPos);
                }

                int consumed = (int)total;
                Buffer.BlockCopy(_buffer, consumed, _buffer, 0, _bufferCount - consumed);
                _bufferCount -= consumed;

                if (_closeRequested)
                    return;
            }
        }

        void HandleDataFrame(bool fin, int opcode, int payloadStart, int length, int maskPos)
        {
            if (maskPos >= 0)
                Unmask(payloadStart, length, maskPos);

            if (opcode == 0x0)
            {
                // Continuation of an open fragmented message.
                if (_fragment == null)
                {
                    Fail("continuation frame with no message in progress");
                    return;
                }

                _fragment.Write(_buffer, payloadStart, length);
                if (fin)
                {
                    byte[] payload = _fragment.ToArray();
                    int messageOpcode = _fragmentOpcode;
                    DisposeFragment();
                    CompleteMessage(messageOpcode, payload);
                }
            }
            else if (opcode == 0x1 || opcode == 0x2)
            {
                if (_fragment != null)
                {
                    Fail("new data frame while a fragmented message is open");
                    return;
                }

                if (fin)
                {
                    var payload = new byte[length];
                    if (length > 0)
                        Buffer.BlockCopy(_buffer, payloadStart, payload, 0, length);
                    CompleteMessage(opcode, payload);
                }
                else
                {
                    _fragment = new MemoryStream();
                    _fragmentOpcode = opcode;
                    _fragment.Write(_buffer, payloadStart, length);
                }
            }
            else
            {
                Fail("unknown opcode " + opcode);
            }
        }

        void CompleteMessage(int opcode, byte[] payload)
        {
            if (opcode == 0x1)
            {
                _incoming.Enqueue(new WebSocketMessage
                {
                    Kind = WebSocketMessageKind.Text,
                    Text = Encoding.UTF8.GetString(payload),
                });
            }
            else
            {
                _incoming.Enqueue(new WebSocketMessage
                {
                    Kind = WebSocketMessageKind.Binary,
                    Binary = payload,
                });
            }
        }

        void HandleControlFrame(int opcode, int payloadStart, int length, int maskPos)
        {
            if (maskPos >= 0)
                Unmask(payloadStart, length, maskPos);

            if (opcode == 0x8)
            {
                // Record why before echoing. A close frame is the only place the
                // server says why it gave up, and without this the caller only ever
                // sees "closed by peer" and has to guess. With it, a rejected frame
                // reads as "closed by peer: 1002 incorrect masking".
                RecordCloseReason(payloadStart, length);

                // Echo the close and stop. The payload is a status code we do not
                // need to act on; echoing it is the polite response.
                SendFrame(0x8, CopyOf(payloadStart, length));
                _peerClosed = true;
                _closeRequested = true;
            }
            else if (opcode == 0x9)
            {
                SendFrame(0xA, CopyOf(payloadStart, length));
            }
            else if (opcode == 0xA)
            {
                // Pong: nothing to do. The service's own liveness ping is answered
                // at the control level, and an application ping/pong is a separate
                // protocol message entirely.
            }
        }

        /// <summary>
        /// Turns a close frame's payload into text on <see cref="LastError"/>.
        ///
        /// The payload is a two-byte big-endian status code followed by an optional
        /// UTF-8 reason. Both are recorded verbatim: the reason is free-form, but
        /// the servers in use do put something useful in it.
        /// </summary>
        void RecordCloseReason(int payloadStart, int length)
        {
            if (length < 2)
            {
                _lastError = "closed by peer";
                return;
            }

            int code = (_buffer[payloadStart] << 8) | _buffer[payloadStart + 1];
            string reason = length > 2
                ? Encoding.UTF8.GetString(_buffer, payloadStart + 2, length - 2)
                : "";

            _lastError = string.IsNullOrEmpty(reason)
                ? $"closed by peer: {code}"
                : $"closed by peer: {code} {reason}";
        }

        void DisposeFragment()
        {
            if (_fragment != null)
            {
                _fragment.Dispose();
                _fragment = null;
            }

            _fragmentOpcode = 0;
        }

        void Unmask(int start, int length, int maskPos)
        {
            for (int i = 0; i < length; i++)
                _buffer[start + i] = (byte)(_buffer[start + i] ^ _buffer[maskPos + (i & 3)]);
        }

        byte[] CopyOf(int start, int length)
        {
            var copy = new byte[length];
            if (length > 0)
                Buffer.BlockCopy(_buffer, start, copy, 0, length);
            return copy;
        }

        void Fail(string reason)
        {
            _lastError = reason;
            _closeRequested = true;
        }

        // ---- send -----------------------------------------------------------

        bool SendFrame(int opcode, byte[] payload)
        {
            try
            {
                byte[] frame = BuildFrame(opcode, payload);
                lock (_sendLock)
                {
                    NetworkStream stream = _stream;
                    if (stream == null)
                    {
                        _lastError = "not connected";
                        return false;
                    }

                    stream.Write(frame, 0, frame.Length);
                    stream.Flush();
                }

                return true;
            }
            catch (Exception e)
            {
                _lastError = "send failed: " + e.Message;
                return false;
            }
        }

        /// <summary>
        /// Builds a single, fully-masked frame. A client must mask every frame it
        /// sends, so this always sets the mask bit and a fresh key.
        /// </summary>
        static byte[] BuildFrame(int opcode, byte[] payload)
        {
            int length = payload?.Length ?? 0;
            int extended = length >= 65536 ? 8 : length >= 126 ? 2 : 0;

            var frame = new byte[2 + extended + 4 + length];
            frame[0] = (byte)(0x80 | (opcode & 0x0F));

            // The mask bit is not optional and is not set anywhere else: RFC 6455
            // requires every frame a client sends to be masked, and a conforming
            // server is entitled to fail the connection with 1002 "incorrect
            // masking" on the first frame that is not. The mask key and the masking
            // loop below are dead weight without it, so it goes into the second byte
            // here, for all three length forms.
            int pos;
            if (extended == 8)
            {
                frame[1] = (byte)(0x80 | 127);
                ulong value = (ulong)length;
                for (int i = 0; i < 8; i++)
                    frame[2 + i] = (byte)(value >> (56 - 8 * i));
                pos = 10;
            }
            else if (extended == 2)
            {
                frame[1] = (byte)(0x80 | 126);
                frame[2] = (byte)(length >> 8);
                frame[3] = (byte)length;
                pos = 4;
            }
            else
            {
                frame[1] = (byte)(0x80 | length);
                pos = 2;
            }

            var key = new byte[4];
            using (var rng = RandomNumberGenerator.Create())
                rng.GetBytes(key);

            frame[pos] = key[0];
            frame[pos + 1] = key[1];
            frame[pos + 2] = key[2];
            frame[pos + 3] = key[3];

            int payloadStart = pos + 4;
            for (int i = 0; i < length; i++)
                frame[payloadStart + i] = (byte)(payload[i] ^ key[i & 3]);

            return frame;
        }

        // ---- teardown -------------------------------------------------------

        void CloseInternal(bool joinThread)
        {
            CloseSockets();

            Thread thread = _thread;
            if (joinThread && thread != null && thread != Thread.CurrentThread && thread.IsAlive)
                thread.Join(CloseJoinTimeoutMs);

            if (thread == Thread.CurrentThread)
                return;

            _thread = null;
        }

        void CloseSockets()
        {
            try
            {
                _stream?.Close();
            }
            catch
            {
                // Closing a broken stream is not worth reporting.
            }

            try
            {
                _client?.Close();
            }
            catch
            {
            }

            _stream = null;
            _client = null;
        }

        void DrainIncoming()
        {
            while (_incoming.TryDequeue(out _))
            {
            }
        }
    }
}
