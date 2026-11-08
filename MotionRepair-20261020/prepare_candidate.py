"""Create new motion sources and packages; existing project files stay read-only."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import hashlib

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SOURCE = PROJECT / 'unity-client/Assets/MGFR/StructuredVoiceFinal'
BASE = PROJECT / 'SiLLMBridge-20261020/MainPlayer-StructuredVoice'

FIELDS = '''
  sealed class CachedClip {public int frames;public float fps;public float[] values;}
  readonly Dictionary<int,CachedClip> cached=new Dictionary<int,CachedClip>();
  Quaternion[] finalPose,transitionPose; bool poseReady;string cueKey="";
  float blendStarted,actionStarted;int heldClip=-1;string heldKey="";
  float sampleNow;public float ReviewDelta=1f/60f;
  public bool ReviewManual;public int ClipReads {get;private set;}
  public float MotionClock=>clipClock;
  public void StepReview(float now,float delta){ReviewClock=now;ReviewDelta=delta;LateUpdate();}
  void CacheClip(int index){
   if(cached.ContainsKey(index))return;
   using(var reader=new BinaryReader(File.OpenRead(Path.Combine(root,"motions",motions.clips[index].file)))){
    if(Encoding.ASCII.GetString(reader.ReadBytes(8))!="ENFMOT1\\0"||reader.ReadInt32()!=rig.nodes.Length)throw new InvalidDataException("Motion skeleton contract");
    int count=reader.ReadInt32();float rate=reader.ReadSingle();
    if(count<2||rate<=0||rate>240)throw new InvalidDataException("Motion sampling contract");
    var bytes=reader.ReadBytes(checked(count*rig.nodes.Length*40));
    if(bytes.Length!=count*rig.nodes.Length*40)throw new InvalidDataException("Truncated motion");
    var values=new float[bytes.Length/4];Buffer.BlockCopy(bytes,0,values,0,bytes.Length);
    cached.Add(index,new CachedClip{frames=count,fps=rate,values=values});ClipReads++;
   }
  }
'''

LOAD = '''  void Load(int index){
   if(active==index)return;
   if(!cached.TryGetValue(index,out var data))throw new InvalidOperationException("Clip was not preloaded");
   active=index;frames=data.frames;fps=data.fps;motion=data.values;CurrentAction=motions.clips[index].name;
  }
'''

TICK = '''  void LateUpdate(){
   if(!Ready||ReviewManual&&ReviewClock<0)return;
   float now=ReviewClock>=0?ReviewClock:Time.unscaledTime;
   float dt=Mathf.Clamp(ReviewClock>=0?ReviewDelta:Time.unscaledDeltaTime,.0001f,.05f);sampleNow=now;
   string value=Interlocked.Exchange(ref json,null);
   if(value!=null&&!ReviewOverride){try{
    var incoming=JsonUtility.FromJson<SpeechPlan>(value);
    if(incoming!=null&&incoming.sequence!=seenSequence){plan=incoming;seenSequence=incoming.sequence;heard=false;planStart=-1;genericStart=now;heldClip=-1;}
   }catch(Exception e){Debug.LogWarning("MGFR plan rejected: "+e.GetType().Name);}}
   bool audible=ReviewOverride?ReviewSpeaking:voice.IsSpeaking;
   bool matches=plan!=null&&(plan.voice_round<0||plan.voice_round==voice.CurrentRound);
   bool generic=matches&&plan.voice_round<0&&now-genericStart<plan.speech_duration;
   if(matches&&(audible||generic)){if(!heard){heard=true;planStart=now;}lastAudible=now;}
   bool pending=audio!=null&&audio.PlaybackPending;
   bool playing=matches&&heard&&(audible||generic||(plan.voice_round>=0&&(pending||now-lastAudible<.28f)));
   if(!matches){heard=false;heldClip=-1;}
   // The old idle owns its own continuous base. It never receives final IK output.
   idle.Apply(now,dt);
   for(int i=0;i<targets.Length;i++)baseWorld[i]=targets[i].rotation;
   var baseLocal=new Quaternion[targets.Length];for(int i=0;i<targets.Length;i++)baseLocal[i]=targets[i].localRotation;
   string selected="idle",nextKey="idle";float seconds=0;int chosen=-1;
   float elapsed=heard?Mathf.Max(0,now-planStart):0;
   if(playing&&plan.actions!=null)for(int i=0;i<plan.actions.Length;i++){
    var cue=plan.actions[i];if(cue==null||!ReviewedActions.Contains(cue.name)||cue.name=="idle"||!actionIndices.TryGetValue(cue.name,out int index))continue;
    float length=Mathf.Min(cue.duration,motions.clips[index].duration);
    if(cue.at<=elapsed&&elapsed<cue.at+length){chosen=index;nextKey=seenSequence+":"+i;seconds=elapsed-cue.at;break;}
   }
   if(chosen>=0){
    if(heldKey!=nextKey){heldKey=nextKey;heldClip=chosen;actionStarted=now-seconds;}
   }else if(heldClip>=0&&matches&&heard&&now-actionStarted<motions.clips[heldClip].duration){
    // Finish a started authored gesture across sentence gaps and normal audio end.
    chosen=heldClip;nextKey=heldKey;seconds=now-actionStarted;
   }else heldClip=-1;
   if(chosen>=0)selected=motions.clips[chosen].name;
   BodyWeight=Mathf.MoveTowards(BodyWeight,chosen>=0?1:0,dt/.4f);
   EmotionWeight=Mathf.MoveTowards(EmotionWeight,playing&&plan.expression_variant!="native"?Mathf.Clamp01(plan.emotion_intensity):0,dt/.45f);
   if(nextKey!=cueKey){
    cueKey=nextKey;blendStarted=now;
    for(int i=0;i<targets.Length;i++)transitionPose[i]=poseReady?finalPose[i]:baseLocal[i];
   }
   Load(chosen>=0?chosen:actionIndices["idle"]);clipClock=seconds;
   if(chosen>=0){
    float frame=Mathf.Clamp(seconds*fps,0,frames-1);int a=(int)frame,b=Mathf.Min(a+1,frames-1);float t=frame-a;
    for(int i=0;i<rig.nodes.Length;i++){
     int x=(a*rig.nodes.Length+i)*10,y=(b*rig.nodes.Length+i)*10;
     sourceLocal[i]=Quaternion.Slerp(new Quaternion(motion[x],motion[x+1],motion[x+2],motion[x+3]),new Quaternion(motion[y],motion[y+1],motion[y+2],motion[y+3]),t);
     int parent=rig.nodes[i].parent;sourceWorld[i]=parent<0?sourceLocal[i]:sourceWorld[parent]*sourceLocal[i];
     var pos=Vector3.Lerp(new Vector3(motion[x+4],motion[x+5],motion[x+6]),new Vector3(motion[y+4],motion[y+5],motion[y+6]),t);
     var scale=Vector3.Lerp(new Vector3(motion[x+7],motion[x+8],motion[x+9]),new Vector3(motion[y+7],motion[y+8],motion[y+9]),t);
     sourcePosition[i]=parent<0?pos:sourcePosition[parent]+sourceWorld[parent]*Vector3.Scale(sourceScale[parent],pos);
     sourceScale[i]=parent<0?scale:Vector3.Scale(sourceScale[parent],scale);
    }
    for(int i=0;i<targets.Length;i++){
     string n=targets[i].name;if(n=="頭"||n=="首"||IsArm(n)||IsLower(n))continue;
     int s=sourceIndices[i];var delta=faceTurn*(sourceWorld[s]*Quaternion.Inverse(sourceRest[s]))*Quaternion.Inverse(faceTurn);
     targets[i].rotation=loader.transform.rotation*delta*targetRest[i];
    }
    // Solve the full target first. Fading the IK input made the collision guard snap on.
    foreach(var arm in arms)ApplyNativeArm(arm,1);
   }
   float fade=Mathf.SmoothStep(0,1,Mathf.Clamp01((now-blendStarted)/.48f));
   for(int i=0;i<targets.Length;i++){
    string n=targets[i].name;if(n=="頭"||n=="首"||IsLower(n))continue;
    var target=Quaternion.Slerp(transitionPose[i],targets[i].localRotation,fade);
    if(poseReady){
     var smooth=Quaternion.Slerp(finalPose[i],target,1-Mathf.Exp(-dt/.045f));
     target=Quaternion.RotateTowards(finalPose[i],smooth,(IsArm(n)?240f:140f)*dt);
    }
    targets[i].localRotation=finalPose[i]=target;
   }
   poseReady=true;MinArmClearance=ArmClearance();
   if(attention!=null&&chosen>=0){int h=Array.FindIndex(rig.nodes,n=>n.name=="Bip001_Head");
    var rest=new Quaternion(rig.nodes[h].q[0],rig.nodes[h].q[1],rig.nodes[h].q[2],rig.nodes[h].q[3]);var q=faceTurn*(sourceLocal[h]*Quaternion.Inverse(rest))*Quaternion.Inverse(faceTurn);var e=q.eulerAngles;
    attention.SubmitHeadGesture(new Vector3(Mathf.DeltaAngle(0,e.x),Mathf.DeltaAngle(0,e.y),Mathf.DeltaAngle(0,e.z))*fade,Time.unscaledTime);
   }
  }
  static bool IsLower(string n)=>n=="下半身"||n.Contains("足")||n.Contains("ひざ")||n.Contains("つま先");
'''

def create(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(text)

def make_sources(folder, repair):
    text=(SOURCE/'MainAvatarActions.cs').read_text(encoding='utf-8-sig')
    marker='   if(Array.IndexOf(args,"-mgfr-actions-review")>=0)'
    text=text.replace(marker,'   if(Array.IndexOf(args,"-mgfr-motion-review")>=0)new GameObject("Motion continuity review").AddComponent<MotionContinuityReview>();\n'+marker)
    if repair:
        text=text.replace('  void Load(int index)', FIELDS+'  void Load(int index)',1)
        start=text.index('  void Load(int index)');end=text.index('  public void SetReviewPlan',start)
        text=text[:start]+LOAD+text[end:]
        start=text.index('  void LateUpdate(){if(!Ready)return;');end=text.index('  public void ReviewAt',start)
        text=text[:start]+TICK+text[end:]
        text=text.replace('idle.enabled=false;Load(actionIndices["idle"]);','idle.enabled=false;finalPose=new Quaternion[targets.Length];transitionPose=new Quaternion[targets.Length];foreach(var item in actionIndices)if(ReviewedActions.Contains(item.Key))CacheClip(item.Value);Load(actionIndices["idle"]);')
        text=text.replace('planStart=Time.unscaledTime;genericStart=planStart;heard=false;', 'planStart=ReviewClock>=0?ReviewClock:Time.unscaledTime;genericStart=planStart;heard=false;heldClip=-1;heldKey="";')
    else:
        text=text.replace('  public void ReviewAt(float seconds)', '  public bool ReviewManual;public float ReviewDelta=1f/60f;public int ClipReads=>-1;public float MotionClock=>clipClock;public void StepReview(float now,float delta){ReviewClock=now;LateUpdate();}\n  public void ReviewAt(float seconds)')
    create(folder/'MainAvatarActions.cs',text)
    for name in ['MainActionsReview.cs','MainNetworkReview.cs']:
        create(folder/name,(SOURCE/name).read_text(encoding='utf-8-sig'))
    create(folder/'MotionContinuityReview.cs',(ROOT/'MotionContinuityReview.cs').read_text(encoding='utf-8-sig'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--baseline',action='store_true');args=parser.parse_args()
    output=ROOT/args.name
    if output.exists() or output.parent!=ROOT:raise RuntimeError('Requires new direct child directory')
    output.mkdir();src=output/'Source';src.mkdir();make_sources(src,not args.baseline)
    work=output/'Build';work.mkdir();managed=BASE/'MGFR_Data/Managed'
    plugin=work/'MGFR.StructuredVoiceFinal.dll'
    options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/debug:portable','/out:'+str(plugin)]
    options+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!='MGFR.StructuredVoiceFinal.dll']
    options += [str(p) for p in src.glob('*.cs')]
    create(work/'compile.rsp','\n'.join('"'+x+'"' for x in options))
    subprocess.run([str(PROJECT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(PROJECT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(work/'compile.rsp')],check=True)
    package=output/'Player';package.mkdir()
    for source in BASE.rglob('*'):
        if not source.is_file():continue
        rel=source.relative_to(BASE)
        if rel.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:continue
        target=package/rel;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(source.read_bytes())
    for name in ['MGFR.StructuredVoiceFinal.dll','MGFR.StructuredVoiceFinal.pdb']:
        with (package/'MGFR_Data/Managed'/name).open('xb') as f:f.write((work/name).read_bytes())
    create(output/'receipt.json',json.dumps({'base':str(BASE),'candidate':str(package),'repair':not args.baseline,'source_sha256':hashlib.sha256((src/'MainAvatarActions.cs').read_bytes()).hexdigest()},indent=2))
    print('READY',package/'MGFR.exe')

if __name__=='__main__':main()
