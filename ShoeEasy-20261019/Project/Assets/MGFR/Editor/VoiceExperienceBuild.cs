using System;
using UnityEngine;
using MGFR.Experience;

namespace MGFR.Dialogue
{
 public static class VoiceExperienceBuild
 {
  public static void Build()
  {
   var state=new SpeechMotionState();float maxStep=0,previous=0;double time=0;
   for(int i=0;i<60;i++){state.Tick(false,true,1,time,1f/60);time+=1d/60;}
   if(state.Weight!=0)throw new Exception("Motion must wait for actual playback");
   for(int i=0;i<120;i++){state.Tick(true,true,1,time,1f/60);time+=1d/60;maxStep=Mathf.Max(maxStep,Mathf.Abs(state.Weight-previous));previous=state.Weight;}
   float peak=state.Weight;
   for(int i=0;i<120;i++){state.Tick(false,false,1,time,1f/60);time+=1d/60;maxStep=Mathf.Max(maxStep,Mathf.Abs(state.Weight-previous));previous=state.Weight;}
   if(peak<.99f||state.Weight>.01f||maxStep>.09f)throw new Exception("Speech blend is abrupt or does not return to idle");
   if(SpeechMotionState.AffectsBone(21)||SpeechMotionState.AffectsBone(25))throw new Exception("Talking must not override leg planting");
   var packet=MicrophonePacket.Encode(new float[320],1,16000,7,9);
   if(packet.Length!=664||packet[0]!=1||packet[1]!=1||packet[4]!=7||packet[8]!=9||packet[22]!=20)throw new Exception("Microphone packet wire layout mismatch");
   Debug.Log($"[MGFR voice checks] PASS waitsForActualPlayback=True blendPeak={peak:F4} blendEnd={state.Weight:F4} maxWeightStep={maxStep:F4} legsPreserved=True microphoneFrameBytes={packet.Length}");
   MGFR.BareHands.ContinuousHandsBuild.Build();
  }
 }
}
