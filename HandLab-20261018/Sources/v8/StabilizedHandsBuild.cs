using System;
using UnityEngine;

namespace MGFR.BareHands
{
 public static class StabilizedHandsBuild
 {
  static HandFrame Raw(Vector3 shift)
  {
   var f=new HandFrame{Tracked=true,ValidCount=26};
   f.Joints[1]=new Pose(shift,Quaternion.identity);f.Joints[0]=new Pose(shift+Vector3.up*.04f,Quaternion.identity);
   f.Joints[2]=new Pose(shift+new Vector3(-.025f,.02f,0),Quaternion.identity);
   for(int i=3;i<6;i++)f.Joints[i]=new Pose(f.Joints[i-1].position+new Vector3(-.015f,.02f,0),Quaternion.identity);
   for(int finger=0;finger<4;finger++)for(int j=0;j<5;j++)f.Joints[6+finger*5+j]=new Pose(shift+new Vector3(-.03f+finger*.02f,.025f+j*.025f,0),Quaternion.identity);
   for(int i=0;i<26;i++){f.Valid[i]=true;f.Radius[i]=.008f;}
   return f;
  }
  public static void Build()
  {
   var filter=new HandPoseStabilizer();var output=new HandFrame();double t=1;float rawEnergy=0,filteredEnergy=0;
   for(int frame=0;frame<180;frame++)
   {
    var raw=Raw(Vector3.right*(frame%2==0?.003f:-.003f));filter.Process(raw,output,t);t+=1d/72;
    if(frame>40){rawEnergy+=raw.Joints[1].position.sqrMagnitude;filteredEnergy+=output.Joints[1].position.sqrMagnitude;}
   }
   float ratio=Mathf.Sqrt(filteredEnergy/rawEnergy);if(ratio>.65f)throw new Exception("Stationary jitter reduction failed "+ratio);
   float maxLag=0;
   for(int frame=0;frame<72;frame++)
   {
    var raw=Raw(Vector3.right*(frame/72f));filter.Process(raw,output,t);t+=1d/72;
    maxLag=Mathf.Max(maxLag,Vector3.Distance(raw.Joints[1].position,output.Joints[1].position));
   }
   if(maxLag>.04f)throw new Exception("Moving hand lag too high "+maxLag);
   var missing=Raw(Vector3.right);missing.Valid[10]=false;filter.Process(missing,output,t);t+=1d/72;
   if(!output.Valid[10]||output.Observed[10]||output.CanStartPinch)throw new Exception("Short missing tip must be held without starting a grab");
   filter.Process(missing,output,t+.08);
   if(output.Valid[10])throw new Exception("Held finger must expire");
   missing.Valid[1]=false;filter.Process(missing,output,t+.1);
   if(output.Tracked||output.ValidCount!=0)throw new Exception("Lost wrist must release immediately");
   filter.Reset();var baseline=Raw(Vector3.zero);filter.Process(baseline,output,t+.2);
   float length=Vector3.Distance(output.Joints[10].position,output.Joints[9].position);
   baseline.Joints[10].position+=Vector3.right*.08f;filter.Process(baseline,output,t+.22);
   float after=Vector3.Distance(output.Joints[10].position,output.Joints[9].position);
   if(Mathf.Abs(after-length)>.001f)throw new Exception("Finger length jumped "+after);
   filter.Reset();var curled=Raw(Vector3.zero);
   for(int i=8;i<=10;i++){curled.Joints[i].position=curled.Joints[i-1].position+Quaternion.Euler(75,0,0)*Vector3.up*.025f;curled.Joints[i].rotation=Quaternion.Euler(75,0,0);}
   for(int frame=0;frame<36;frame++){filter.Process(curled,output,t+.3+frame/72d);}
   if(Vector3.Distance(output.Joints[10].position,curled.Joints[10].position*HandPoseStabilizer.SizeGain)>.008f)throw new Exception("Curled finger did not follow");
   Debug.Log($"[MGFR hand stability checks] PASS jitterRmsRatio={ratio:F3} movingWristLagMetres={maxLag:F4} partialLossGrace=60ms predictedTipCannotStartGrab=True lostWristReleases=True boneLengthStable=True curledFingerFollows=True sizeGain=1.05");
   SkinnedHandsBuild.Build();
  }
 }
}
