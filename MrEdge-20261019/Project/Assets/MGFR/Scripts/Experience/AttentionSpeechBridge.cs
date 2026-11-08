using System.Collections;
using UnityEngine;
using MGFR.Attention;
using MGFR.Dialogue;

namespace MGFR.Experience
{
    public sealed class AttentionSpeechBridge : MonoBehaviour
    {
        FaceAttentionController face;
        DialogueClient client;
        bool wasSpeaking;
        string lastUser="";float shyUntil;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()=>new GameObject("Attention speech bridge").AddComponent<AttentionSpeechBridge>();
        IEnumerator Start()
        {
            while((face=FindAnyObjectByType<FaceAttentionController>())==null)yield return null;
            while((client=FindAnyObjectByType<DialogueClient>())==null)yield return null;
        }
        void Update()
        {
            if(face==null||client==null)return;
            if(client.LastAsrText!=lastUser)
            {
                lastUser=client.LastAsrText;
                if(InputIsAffectionate(lastUser))
                {face.SetMood(FaceMood.Shy,Time.unscaledTime);shyUntil=Time.unscaledTime+3;}
            }
            bool speaking=client.IsSpeaking;
            // Sentence mood now begins at its actual audio cursor in the motion
            // player, rather than once with an incomplete streamed reply.
            if(speaking&&!wasSpeaking&&Time.unscaledTime<shyUntil)face.SetMood(FaceMood.Shy,Time.unscaledTime);
            if(!speaking&&wasSpeaking)face.EndSpokenLine();
            wasSpeaking=speaking;
        }
        public static bool InputIsAffectionate(string text)
        {
            if(string.IsNullOrEmpty(text))return false;
            foreach(var phrase in new[]{"真可爱","好可爱","很可爱","真好看","很漂亮","真漂亮","喜欢你","想你了","抱抱","亲一下"})
            {
                int at=text.IndexOf(phrase,System.StringComparison.Ordinal);if(at<0)continue;
                string prefix=text.Substring(System.Math.Max(0,at-4),System.Math.Min(4,at));
                if(!prefix.Contains("不")&&!prefix.Contains("没"))return true;
            }
            return false;
        }
    }
}
