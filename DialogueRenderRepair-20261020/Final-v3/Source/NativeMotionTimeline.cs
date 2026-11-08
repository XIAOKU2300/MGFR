using System;
using System.Collections.Generic;

namespace MGFR.StructuredVoiceFinal {
 // A local graph of already installed official clips. It never edits samples,
 // changes clip speed or exposes additional actions to the language model.
 public sealed class NativeMotionTimeline {
  public sealed class Clip {public string name,source;public float duration;public bool loop;}
  public sealed class Cue {public string name;public float at,duration;}
  sealed class Request {public float at;public readonly List<Clip> phases=new List<Clip>();public readonly List<float> lengths=new List<float>();}
  readonly Dictionary<string,Clip> clips;
  readonly Dictionary<string,Clip> bySource=new Dictionary<string,Clip>();
  readonly List<Request> requests=new List<Request>();
  int next,phase,serial;Request active;
  public Clip Current {get;private set;}
  public float PhaseTime {get;private set;}
  string key="idle";public string Key=>key;
  public int EnteredPhases {get;private set;}
  public NativeMotionTimeline(Dictionary<string,Clip> values){clips=values;foreach(var c in values.Values)if(!string.IsNullOrEmpty(c.source))bySource[c.source]=c;}
  static string Family(string source){
   if(source==null)return null;
   foreach(var suffix in new[]{"_start","_loop","_end"})if(source.EndsWith(suffix,StringComparison.Ordinal))return source.Substring(0,source.Length-suffix.Length);
   return null;
  }
  public void Begin(Cue[] cues){
   requests.Clear();next=0;active=null;Current=null;PhaseTime=0;serial++;key="idle";
   string lastFamily=null;Request previous=null;
   if(cues==null)return;
   foreach(var cue in cues){
    if(cue==null||cue.name=="idle"||!clips.TryGetValue(cue.name,out var selected))continue;
    string family=Family(selected.source);
    // An LLM may explicitly list all three phases. Play that family once.
    if(family!=null&&family==lastFamily&&previous!=null&&previous.phases.Count==3){
     // Keep an explicit late exit in the public timetable. The native loop
     // repeats at its original speed rather than ignoring the requested exit.
     if(selected.source.EndsWith("_end",StringComparison.Ordinal))previous.lengths[1]=Math.Max(previous.lengths[1],cue.at-previous.at-previous.lengths[0]);
     continue;
    }
    lastFamily=family;
    var request=new Request{at=Math.Max(0,cue.at)};
    if(family!=null && !selected.source.EndsWith("_end",StringComparison.Ordinal)
       && bySource.TryGetValue(family+"_start",out var start)
       && bySource.TryGetValue(family+"_loop",out var loop)
       && bySource.TryGetValue(family+"_end",out var end)){
     request.phases.Add(start);request.phases.Add(loop);request.phases.Add(end);
    }else request.phases.Add(selected);
    foreach(var c in request.phases)request.lengths.Add(c.duration);
    requests.Add(request);previous=request;
   }
   requests.Sort((a,b)=>a.at.CompareTo(b.at));
  }
  public void Cancel(){requests.Clear();next=0;active=null;Current=null;PhaseTime=0;serial++;key="idle";}
  public void Tick(float delta,float speechSeconds,bool speechActive,bool interrupted,bool utteranceEnded=false){
   if(interrupted){Cancel();return;}
   if(active!=null){
    PhaseTime+=Math.Max(0,delta);
    while(active!=null&&PhaseTime>=active.lengths[phase]){
     PhaseTime-=active.lengths[phase];phase++;
     if(phase<active.phases.Count){Current=active.phases[phase];EnteredPhases++;key=serial+":"+phase;}
     else{active=null;Current=null;PhaseTime=0;key="idle";}
    }
   }
   if(active==null && speechActive && next<requests.Count && speechSeconds>=requests[next].at){
    active=requests[next++];phase=0;Current=active.phases[phase];PhaseTime=0;serial++;EnteredPhases++;key=serial+":"+phase;
   }
   // A completed utterance cannot cause a future delayed cue to start afterward.
   if(utteranceEnded&&!speechActive&&active==null&&next<requests.Count&&speechSeconds<requests[next].at)next=requests.Count;
  }
 }
}
