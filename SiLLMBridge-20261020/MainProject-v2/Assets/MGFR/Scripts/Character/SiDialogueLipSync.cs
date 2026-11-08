using MGFR.Dialogue;
using UnityEngine;

namespace MGFR.Character
{
    /// <summary>
    /// Feeds the character's mouth from the audio that is actually being played.
    ///
    /// It reads <see cref="DialogueClient.IsSpeaking"/> and
    /// <see cref="DialogueClient.CurrentLevel"/> rather than the server's state
    /// message, and that is the whole point: the server saying "speaking" only means
    /// it has sent audio, while these two reflect what is coming out of the mixer
    /// right now. So when playback is interrupted, when the queue runs dry, or when
    /// the socket drops, the level falls to zero on its own and the mouth closes
    /// without this component needing to know why.
    ///
    /// Nothing here touches the network. It reads two floats that the client already
    /// computed on the main thread.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class SiDialogueLipSync : MonoBehaviour
    {
        [SerializeField] DialogueClient _client;
        [SerializeField] SiCharacterController _controller;

        [Tooltip("Log the level a few times a second. Noisy; for checking the wiring.")]
        public bool verbose;

        float _nextLog;
        float _peak;

        public void Bind(DialogueClient client, SiCharacterController controller)
        {
            _client = client;
            _controller = controller;
        }

        void Update()
        {
            if (_client == null || _controller == null)
                return;

            var speaking = _client.IsSpeaking;
            var level = _client.CurrentLevel;
            _controller.SetMouth(level, speaking);

            if (verbose)
            {
                _peak = Mathf.Max(_peak, level);
                if (Time.unscaledTime >= _nextLog)
                {
                    _nextLog = Time.unscaledTime + 1f;
                    Debug.Log($"[SiDialogueLipSync] speaking={speaking} level={level:F3} peak={_peak:F3} "
                            + $"queued={_client.QueuedSamples} dropped={_client.DroppedAudioFrames}");
                    _peak = 0f;
                }
            }
        }
    }
}
