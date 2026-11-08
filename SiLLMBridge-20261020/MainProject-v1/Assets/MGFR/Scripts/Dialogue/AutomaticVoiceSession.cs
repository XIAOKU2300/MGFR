using System;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;

namespace MGFR.Dialogue
{
 [DefaultExecutionOrder(50)]
 public sealed class AutomaticVoiceSession:MonoBehaviour
 {
  public bool SessionStarted {get;private set;}
  public bool Muted {get;private set;}
  public bool CaptureRunning=>clip!=null;
  public string DeviceLabel=>device??"系统默认麦克风";
  public string Status {get;private set;}="正在连接语音服务";
  public int SentFrames {get;private set;}
  public float MicLevel {get;private set;}
  public bool TestInput {get;private set;}
  DialogueClient client;AudioClip clip;float[] capture;string device;string[] devices;Font font;
  bool requested;float nextConnect,echoUntil;int readPosition,frameSamples,deviceChoice;ulong sequence;
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Install()
  {
   if(SceneManager.GetActiveScene().name!=SiCharacterBootstrap.SceneName)return;
   var args=Environment.GetCommandLineArgs();
   if(Array.Exists(args,a=>a=="-mgfr-coexist-review"||a=="-mgfr-controller-review"||a=="-mgfr-floor-review"||a=="-mgfr-unified-review"||a=="-mgfr-shoe-review"||a=="-mgfr-wardrobe-review"||a=="-mgfr-cloth-motion-review"||a=="-mgfr-performance-review"||a=="-mgfr-chat-review"||a=="-mgfr-audio-review"||a=="-mgfr-selftest"||a=="-mgfr-hand-review"||a=="-mgfr-contact-stress"||a=="-mgfr-physics-review"||a=="-mgfr-render-review"||a=="-mgfr-experience-check"))return;
   new GameObject("Automatic voice conversation").AddComponent<AutomaticVoiceSession>();
  }
  void Start()
  {
   client=FindAnyObjectByType<DialogueClient>();devices=Microphone.devices;
   TestInput=Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-voice-review")>=0;
   font=Font.CreateDynamicFontFromOSFont("Microsoft YaHei",16);
  }
  void Update()
  {
   if(client==null){client=FindAnyObjectByType<DialogueClient>();return;}
   if(Input.GetKeyDown(KeyCode.F4))Muted=!Muted;
   if(client.State!=DialogueState.Connected)
   {
    requested=SessionStarted=false;StopCapture();
    if(client.State!=DialogueState.Connecting&&Time.unscaledTime>=nextConnect){nextConnect=Time.unscaledTime+3;client.Connect();}
    Status="正在连接语音服务";return;
   }
   if(!requested&&!string.IsNullOrEmpty(client.ServerVersion)){client.StartSession();requested=true;}
   if(requested&&!SessionStarted&&client.ServerState=="listening")
   {
    SessionStarted=true;if(!TestInput)StartCapture();
    Debug.Log("[MGFR auto voice] session listening automatically; input="+(TestInput?"RECORDED_TEST_AUDIO":DeviceLabel));
   }
   if(client.IsSpeaking||client.QueuedSamples>0)echoUntil=Time.unscaledTime+.3f;
   Status=client.ServerState=="error"?"语音服务出错，请查看对话面板":Muted?"麦克风已静音":client.IsSpeaking?"祀正在说话":client.ServerState=="thinking"?"正在组织回答":client.ServerState=="recognizing"?"正在识别":CaptureRunning||TestInput?"正在听你说话":"没有可用麦克风";
   if(clip==null||!SessionStarted)return;
   int write=Microphone.GetPosition(device);if(write<0)return;
   int available=(write-readPosition+clip.samples)%clip.samples;
   if(available>clip.frequency*.15f){readPosition=(write-frameSamples+clip.samples)%clip.samples;available=frameSamples;}
   while(available>=frameSamples)
   {
    clip.GetData(capture,readPosition);readPosition=(readPosition+frameSamples)%clip.samples;available-=frameSamples;
    float energy=0;foreach(float sample in capture)energy+=sample*sample;MicLevel=Mathf.Sqrt(energy/capture.Length);
    bool suppress=Muted||client.ServerState!="listening"||Time.unscaledTime<echoUntil;
    if(suppress)Array.Clear(capture,0,capture.Length);
    SendSamples(capture,clip.channels,clip.frequency);
   }
  }
  void StartCapture()
  {
   if(devices.Length==0){Status="没有可用麦克风";Debug.LogWarning("[MGFR auto voice] no microphone available");return;}
   clip=Microphone.Start(device,true,5,16000);readPosition=0;
   if(clip==null){Status="麦克风启动失败";return;}
   frameSamples=clip.frequency/50;capture=new float[frameSamples*clip.channels];
   Debug.Log($"[MGFR auto voice] microphone={DeviceLabel} actualRate={clip.frequency} channels={clip.channels}; F4 mute; microphone suppressed during reply playback");
  }
  public void SendSamples(float[] data,int channels,int rate)
  {
   if(client.SendMicrophoneFrame(MicrophonePacket.Encode(data,channels,rate,(uint)client.CurrentRound,sequence++)))SentFrames++;
  }
  public void SetMuted(bool value){Muted=value;}
  void StopCapture(){if(clip==null)return;Microphone.End(device);Destroy(clip);clip=null;}
  void OnDestroy(){StopCapture();if(font!=null)Destroy(font);}
  void OnGUI()
  {
   var previous=GUI.skin.font;if(font!=null)GUI.skin.font=font;
   GUILayout.BeginArea(new Rect(Screen.width*.5f-195,Screen.height-106,390,98),GUI.skin.box);
   GUILayout.Label("自动语音 · "+Status);
   GUILayout.Label(TestInput?"录音回放验证（不是实机麦克风）":DeviceLabel+" · 音量 "+MicLevel.ToString("F3"));
   GUILayout.BeginHorizontal();
   if(GUILayout.Button(Muted?"取消静音（F4）":"静音（F4）"))Muted=!Muted;
   if(!TestInput&&GUILayout.Button("切换麦克风"))
   {
    StopCapture();deviceChoice=(deviceChoice+1)%(devices.Length+1);device=deviceChoice==0?null:devices[deviceChoice-1];
    if(SessionStarted)StartCapture();
   }
   GUILayout.EndHorizontal();GUILayout.EndArea();GUI.skin.font=previous;
  }
 }
}
