using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.XR;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Skins;
using MGFR.BareHands;
using MGFR.Wardrobe;

namespace MGFR.StructuredVoiceFinal {
 [Serializable] public class ObservedEvent {
  public string event_id,kind,phase,region="unknown",hand="none",part="";
  public int age_ms,duration_ms;
  [NonSerialized] public float created;
 }
 [Serializable] public class ObservedSnapshot {
  public string skin="original",gaze_region="unknown",gaze_source="head_direction",left_touch="unknown",right_touch="unknown";
  public string[] garment_ids=Array.Empty<string>(); public bool[] garment_equipped=Array.Empty<bool>();
 }
 [Serializable] public class ObservedPacket { public string client_id;public long sequence;public ObservedSnapshot snapshot;public ObservedEvent[] events; }
 [Serializable] class ObservationAck {public bool accepted;}

 // Queries only: no new collision response, mesh baking, physics, or body writers.
 [DefaultExecutionOrder(1000)] public sealed class MgfrInteractionContext:MonoBehaviour {
  class Region {public string id;public Transform a,b;public float radius;public Vector3 offset;}
  static readonly int[] TouchJoints={0,5,10,15,20,25};
  readonly List<Region> regions=new List<Region>();
  readonly List<ObservedEvent> pending=new List<ObservedEvent>();
  readonly Dictionary<string,Transform> bones=new Dictionary<string,Transform>();
  SiSkinSwitcher skins;SiCharacterLoader loader;BareHandInteraction hands;WardrobeAdapter wardrobe;
  DialogueClient voice;string endpoint,client=Guid.NewGuid().ToString("N"),skinId="";
  string candidateGaze="unknown",gaze="unknown";readonly string[] touch={"unknown","unknown"};
  readonly bool[] grabbed={false,false};readonly float[] touchedAt=new float[2];
  float gazeSince,nextSample,nextSend;long sequence,eventSequence;bool sending,review;
  public int RegionCount=>regions.Count;public int QueuedEvents=>pending.Count;
  public int SentPackets {get;private set;}public int AcceptedPackets {get;private set;}
  public float MaxSampleMs {get;private set;}public string LastPacket {get;private set;}
  void Start(){
   var args=Environment.GetCommandLineArgs();review=Array.IndexOf(args,"-mgfr-context-review")>=0;
   string url=Arg(args,"-mgfr-service-url","ws://127.0.0.1:8779/ws");
   var uri=new Uri(url);if(!uri.IsLoopback){enabled=false;return;}
   endpoint="http://127.0.0.1:"+uri.Port+"/mgfr-interaction";
  }
  static string Arg(string[] a,string key,string fallback){int i=Array.IndexOf(a,key);return i>=0&&i+1<a.Length?a[i+1]:fallback;}
  void Update(){
   if(Time.unscaledTime<nextSample)return;nextSample=Time.unscaledTime+.1f;
   double started=Time.realtimeSinceStartupAsDouble;
   if(skins==null)skins=FindAnyObjectByType<SiSkinSwitcher>();
   if(voice==null)voice=FindAnyObjectByType<DialogueClient>();
   if(hands==null)hands=FindAnyObjectByType<BareHandInteraction>();
   if(skins==null||!skins.IsReady||voice==null)return;
   if(loader!=skins.Loader||skinId!=skins.CurrentId){loader=skins.Loader;skinId=skins.CurrentId;Bind();}
   var current=WardrobeLiveRuntime.Instance;
   var adapter=current!=null&&current.IsReady?current.Adapter:null;
   if(wardrobe!=adapter){if(wardrobe!=null)wardrobe.Changed-=Garment;wardrobe=adapter;if(wardrobe!=null)wardrobe.Changed+=Garment;}
   if(!review){
    var head=InputDevices.GetDeviceAtXRNode(XRNode.Head);bool tracked=head.isValid&&head.TryGetFeatureValue(CommonUsages.isTracked,out bool valid)&&valid;
    var cam=Camera.main;string hit=tracked&&cam!=null?LookAt(cam.transform.position,cam.transform.forward):"unknown";
    if(hit!=candidateGaze){candidateGaze=hit;gazeSince=Time.unscaledTime;}
    if(hit!=gaze&&(hit=="unknown"||Time.unscaledTime-gazeSince>=.8f))gaze=hit; // passive snapshot only
    for(int h=0;h<2;h++){
     string region="unknown";bool isGrab=false;
     if(hands!=null&&hands.IsReady&&hands.Source!=null&&hands.Source.Frames[h].Tracked){
      var frame=hands.Source.Frames[h];float best=float.PositiveInfinity;
      foreach(int joint in TouchJoints)if(frame.Valid[joint]){
       string r=TouchAt(frame.Joints[joint].position,frame.Radius[joint],out float score);
       if(score<best){best=score;region=r;}
      }
      isGrab=hands.GrabbedBody[h]>=0||(hands.ExternalClothGrab!=null&&hands.ExternalClothGrab(h));
     }
     if(region!=touch[h]){if(touch[h]!="unknown")Add("touch","end",touch[h],h,duration:(int)((Time.unscaledTime-touchedAt[h])*1000));touch[h]=region;touchedAt[h]=Time.unscaledTime;if(region!="unknown")Add("touch","start",region,h);}
     if(isGrab&&!grabbed[h])Add("grab","start",region,h);grabbed[h]=isGrab;
    }
   }
   MaxSampleMs=Mathf.Max(MaxSampleMs,(float)((Time.realtimeSinceStartupAsDouble-started)*1000));
   if(!sending&&voice.State==DialogueState.Connected&&Time.unscaledTime>=nextSend){nextSend=Time.unscaledTime+1;StartCoroutine(Send());}
  }
  void Bind(){
   regions.Clear();bones.Clear();foreach(var bone in loader.Renderer.bones)if(bone!=null&&!bones.ContainsKey(bone.name))bones.Add(bone.name,bone);
   AddRegion("head","頭","頭",.095f,new Vector3(0,.045f,0));
   AddRegion("face","頭","頭",.07f,new Vector3(0,.035f,-.07f));
   AddRegion("shoulder","左腕","右腕",.045f,Vector3.zero);
   AddRegion("torso","上半身","上半身2",.12f,Vector3.zero);
   AddRegion("back","上半身","上半身2",.09f,new Vector3(0,0,.075f));
   AddRegion("waist","下半身","上半身",.11f,Vector3.zero);
   foreach(bool left in new[]{true,false}){
    string side=left?"左":"右",id=left?"left_":"right_";
    AddRegion(id+"arm",side+"腕",side+"ひじ",.045f,Vector3.zero);
    AddRegion(id+"arm",side+"ひじ",side+"手首",.037f,Vector3.zero);
    AddRegion(id+"hand",side+"手首",side+"中指１",.04f,Vector3.zero);
    AddRegion(id+"thigh",side+"足",side+"ひざ",.07f,Vector3.zero);
    AddRegion(id+"calf",side+"ひざ",side+"足首",.045f,Vector3.zero);
    AddRegion(id+"foot",side+"足首",side+"つま先",.045f,Vector3.zero);
   }
   gaze=candidateGaze="unknown";touch[0]=touch[1]="unknown";
  }
  void AddRegion(string id,string first,string second,float radius,Vector3 offset){
   if(!bones.TryGetValue(first,out var a)||!bones.TryGetValue(second,out var b))return;
   regions.Add(new Region{id=id,a=a,b=b,radius=radius,offset=offset});
  }
  void Geometry(Region r,out Vector3 a,out Vector3 b,out float radius){
   float scale=Mathf.Abs(loader.transform.lossyScale.x);Vector3 shift=loader.transform.rotation*(r.offset*scale);
   a=r.a.position+shift;b=r.b.position+shift;radius=r.radius*scale;
  }
  public Vector3 RegionCenter(string id){foreach(var r in regions)if(r.id==id){Geometry(r,out var a,out var b,out _);return(a+b)*.5f;}return Vector3.zero;}
  public string LookAt(Vector3 origin,Vector3 direction){float best=float.PositiveInfinity;string answer="unknown";foreach(var r in regions){Geometry(r,out var a,out var b,out float radius);float distance=RayCapsule(origin,direction.normalized,a,b,radius);if(distance>=0&&distance<best){best=distance;answer=r.id;}}return answer;}
  public string TouchAt(Vector3 point,float handRadius,out float best){best=float.PositiveInfinity;string answer="unknown";foreach(var r in regions){Geometry(r,out var a,out var b,out float radius);float distance=PointSegment(point,a,b);float score=distance/(radius+Mathf.Max(.004f,handRadius));if(score<=1&&score<best){best=score;answer=r.id;}}return answer;}
  static float PointSegment(Vector3 p,Vector3 a,Vector3 b){Vector3 d=b-a;float t=d.sqrMagnitude>1e-8f?Mathf.Clamp01(Vector3.Dot(p-a,d)/d.sqrMagnitude):0;return Vector3.Distance(p,a+t*d);}
  public static float RayCapsule(Vector3 o,Vector3 d,Vector3 a,Vector3 b,float radius){
   Vector3 ba=b-a,oa=o-a;float baba=Vector3.Dot(ba,ba),bard=Vector3.Dot(ba,d),baoa=Vector3.Dot(ba,oa),rdoa=Vector3.Dot(d,oa),oaoa=Vector3.Dot(oa,oa);
   float aa=baba-bard*bard,bb=baba*rdoa-baoa*bard,cc=baba*oaoa-baoa*baoa-radius*radius*baba;
   float disc=bb*bb-aa*cc,best=float.PositiveInfinity;
   if(Mathf.Abs(aa)>1e-8f&&disc>=0){float t=(-bb-Mathf.Sqrt(disc))/aa,y=baoa+t*bard;if(t>=0&&y>=0&&y<=baba)best=t;}
   for(int endpoint=0;endpoint<2;endpoint++){Vector3 oc=o-(endpoint==0?a:b);float p=Vector3.Dot(oc,d),h=p*p-oc.sqrMagnitude+radius*radius;if(h>=0){float t=-p-Mathf.Sqrt(h);if(t>=0)best=Mathf.Min(best,t);}}
   return float.IsPositiveInfinity(best)?-1:best;
  }
  void Garment(string id,bool equipped){Add("garment",equipped?"equipped":"removed","unknown",part:id);}
  void Add(string kind,string phase,string region,int hand=-1,string part="",int duration=0){
   if(pending.Count>=64){Debug.LogWarning("[MGFR context] bounded queue full; observations waiting for connection");return;}
   pending.Add(new ObservedEvent{event_id=client+"-"+(++eventSequence),kind=kind,phase=phase,region=region,hand=hand<0?"none":hand==0?"left":"right",part=part,duration_ms=duration,created=Time.unscaledTime});
   nextSend=Mathf.Min(nextSend,Time.unscaledTime+.12f);
  }
  public void ReviewObserve(string region,int hand=-1){if(!review)return;if(hand<0){gaze=region;}else{touch[hand]=region;Add("touch","start",region,hand);}}
  ObservedSnapshot Snapshot(){
   var s=new ObservedSnapshot{skin=skinId,gaze_region=gaze,left_touch=touch[0],right_touch=touch[1]};
   if(wardrobe!=null){var parts=wardrobe.Profile.parts;s.garment_ids=new string[parts.Length];s.garment_equipped=new bool[parts.Length];for(int i=0;i<parts.Length;i++){s.garment_ids[i]=parts[i].id;s.garment_equipped[i]=wardrobe.IsEquipped(parts[i].id);}}
   return s;
  }
  IEnumerator Send(){
   sending=true;int count=Mathf.Min(16,pending.Count);var batch=pending.GetRange(0,count).ToArray();foreach(var e in batch)e.age_ms=Mathf.Min(120000,(int)((Time.unscaledTime-e.created)*1000));
   var packet=new ObservedPacket{client_id=client,sequence=++sequence,snapshot=Snapshot(),events=batch};LastPacket=JsonUtility.ToJson(packet);SentPackets++;
   using(var request=new UnityWebRequest(endpoint,"POST")){
    request.uploadHandler=new UploadHandlerRaw(Encoding.UTF8.GetBytes(LastPacket));request.downloadHandler=new DownloadHandlerBuffer();request.SetRequestHeader("Content-Type","application/json");request.timeout=2;
    yield return request.SendWebRequest();
    if(request.result==UnityWebRequest.Result.Success){ObservationAck ack=null;try{ack=JsonUtility.FromJson<ObservationAck>(request.downloadHandler.text);}catch(ArgumentException){}if(ack!=null&&ack.accepted){pending.RemoveRange(0,count);AcceptedPackets++;}}
   }
   sending=false;
  }
  void OnDestroy(){if(wardrobe!=null)wardrobe.Changed-=Garment;}
 }
}
