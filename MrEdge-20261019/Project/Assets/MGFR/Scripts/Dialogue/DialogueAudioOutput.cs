using System;
using System.Threading;
using UnityEngine;

namespace MGFR.Dialogue
{
 [DisallowMultipleComponent]
 public sealed class DialogueAudioOutput:MonoBehaviour
 {
  const float PrebufferSeconds=.25f;
  float[] ring,scratch;int outputRate,inputRate;long write,read,flushTarget;int flushCount,lastFlush;
  long sourceFrames,resampledFrames;float lastSample;
  long accepted,played,dropped;int underruns,maxCallback;
  volatile bool active,complete=true,buffering;volatile bool audible;volatile float level;
  AudioSource source;AudioClip carrier;
  public bool IsAudible=>audible;
  public float CurrentLevel=>level;
  public long DroppedSamples=>Volatile.Read(ref dropped);
  public long AcceptedSamples=>Volatile.Read(ref accepted);
  public long PlayedSamples=>Volatile.Read(ref played);
  public int UnderrunEvents=>Volatile.Read(ref underruns);
  public int MaxCallbackFrames=>Volatile.Read(ref maxCallback);
  public bool PlaybackPending=>active;
  public int PlaybackRate=>outputRate;
  // Absolute ring cursors include flushed samples, so interrupted rounds cannot
  // offset the sentence timeline. Read only; the DSP thread remains the owner.
  public long PlaybackCursor=>Volatile.Read(ref read);
  public long WriteCursor=>Volatile.Read(ref write);
  public int QueuedSamples=>(int)Math.Max(0,Volatile.Read(ref write)-Math.Max(Volatile.Read(ref read),Volatile.Read(ref flushTarget)));
  void Awake()
  {
   outputRate=AudioSettings.outputSampleRate;ring=new float[outputRate*60];
   source=GetComponent<AudioSource>();if(source==null)source=gameObject.AddComponent<AudioSource>();
   source.playOnAwake=false;source.loop=true;source.spatialBlend=0;source.volume=1;source.priority=0;
   // The mixer filter pulls at the actual DSP cadence. A one-second streaming
   // PCMReaderCallback can request ahead and pad a short network fragment with silence.
   carrier=AudioClip.Create("MGFR silent DSP carrier",outputRate,1,outputRate,false);
   source.clip=carrier;source.Play();
  }
  public void BeginStream()
  {
   sourceFrames=resampledFrames=0;inputRate=0;lastSample=0;complete=false;buffering=true;active=true;
  }
  public bool CanAccept(int bytes,int channels,int rate)
  {
   if(channels<1||rate<1)return true;
   long needed=(long)Math.Ceiling(bytes/2d/channels*outputRate/rate)+2;
   return needed<=ring.Length-QueuedSamples;
  }
  public void Enqueue(byte[] pcm,int channels,int rate){if(pcm!=null)Enqueue(pcm,0,pcm.Length,channels,rate);}
  public void Enqueue(byte[] pcm,int offset,int count,int channels,int rate)
  {
   if(pcm==null||channels<1||rate<1||count<2||offset<0||offset>pcm.Length-count)return;
   int frames=count/2/channels;if(frames==0)return;
   if(!active)BeginStream();
   if(!CanAccept(count,channels,rate))
   {
    Interlocked.Add(ref dropped,(long)Math.Ceiling(frames*(double)outputRate/rate));
    Debug.LogError("[MGFR stream] playback capacity reached; sender must wait for ring space");return;
   }
   if(inputRate!=rate){inputRate=rate;sourceFrames=resampledFrames=0;}
   if(scratch==null||scratch.Length<frames)scratch=new float[Math.Max(frames,4096)];
   for(int i=0;i<frames;i++)
   {
    float sum=0;for(int c=0;c<channels;c++){int p=offset+2*(i*channels+c);sum+=(short)(pcm[p]|pcm[p+1]<<8)/32768f;}
    scratch[i]=sum/channels;
   }
   long end=sourceFrames+frames,position=write,before=position;
   while(true)
   {
    double at=resampledFrames*(double)inputRate/outputRate;if(at>end-1)break;
    long index=(long)Math.Floor(at);int local=(int)(index-sourceFrames);
    float a=local<0?lastSample:scratch[local];float b=local+1>=frames?scratch[frames-1]:scratch[local+1];
    ring[position%ring.Length]=a+(b-a)*(float)(at-index);position++;resampledFrames++;
   }
   sourceFrames=end;lastSample=scratch[frames-1];Interlocked.Add(ref accepted,position-before);
   Volatile.Write(ref write,position);
  }
  public void CompleteStream()
  {
   if(inputRate>0)
   {
    long target=(long)Math.Round(sourceFrames*(double)outputRate/inputRate),position=write,before=position;
    while(resampledFrames<target){ring[position%ring.Length]=lastSample;position++;resampledFrames++;}
    Interlocked.Add(ref accepted,position-before);Volatile.Write(ref write,position);
   }
   complete=true;
  }
  public void StopAndClear()
  {
   Volatile.Write(ref flushTarget,Volatile.Read(ref write));Interlocked.Increment(ref flushCount);
   complete=true;active=false;buffering=false;audible=false;level=0;
  }
  void OnAudioFilterRead(float[] data,int channels)
  {
   Array.Clear(data,0,data.Length);int frames=data.Length/channels;
   if(frames>maxCallback)maxCallback=frames;
   int flush=Volatile.Read(ref flushCount);if(flush!=lastFlush){lastFlush=flush;read=Volatile.Read(ref flushTarget);}
   long available=Math.Max(0,Volatile.Read(ref write)-read);
   if(!active||(buffering&&!complete&&available<outputRate*PrebufferSeconds)){audible=false;level=0;return;}
   buffering=false;int take=(int)Math.Min(frames,available);double energy=0;
   for(int i=0;i<take;i++)
   {
    float sample=ring[(read+i)%ring.Length];energy+=sample*sample;
    for(int c=0;c<channels;c++)data[i*channels+c]=sample;
   }
   read+=take;Volatile.Write(ref read,read);Interlocked.Add(ref played,take);
   level=take>0?(float)Math.Sqrt(energy/frames):0;audible=take>0&&level>.0005f;
   if(take<frames&&!complete){Interlocked.Increment(ref underruns);buffering=true;}
   if(complete&&read>=Volatile.Read(ref write))active=false;
  }
  void OnDestroy(){if(source!=null)source.Stop();if(carrier!=null)Destroy(carrier);}
 }
}
