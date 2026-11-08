using UnityEngine;

namespace MGFR.BareHands
{
 // Temporal hysteresis measured in seconds, independent of display frame rate.
 public sealed class HandPinchState
 {
  public bool Closed {get;private set;}
  public bool CanAcquire {get;private set;}
  float closeTime,openTime,missingTime;
  public void Reset(){Closed=CanAcquire=false;closeTime=openTime=missingTime=0;}
  public bool Update(HandFrame f,float dt)
  {
   dt=Mathf.Clamp(dt,0,.05f);CanAcquire=false;
   if(!f.Tracked){Reset();return false;}
   if(!f.CanStartPinch)
   {
    missingTime+=dt;closeTime=0;
    if(missingTime>.06f){Closed=false;openTime=0;}
    return Closed;
   }
   missingTime=0;
   // Tip centres do not meet: two fingertip pads have finite thickness.
   float pads=Mathf.Clamp(f.Radius[5]+f.Radius[10],.009f,.032f);
   float close=pads+.006f*f.Scale,open=close+.014f*f.Scale;
   float distance=Vector3.Distance(f.Joints[5].position,f.Joints[10].position);
   if(!Closed)
   {
    closeTime=distance<=close?closeTime+dt:0;
    if(closeTime>=.022f){Closed=true;openTime=0;}
   }
   else
   {
    openTime=distance>=open?openTime+dt:0;
    if(openTime>=.022f){Closed=false;closeTime=0;}
   }
   CanAcquire=Closed&&distance<open;
   return Closed;
  }
 }
}
