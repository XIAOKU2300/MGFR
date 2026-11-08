using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MGFR.Character;
using MGFR.Dialogue;
using MGFR.Skins;
using MGFR.Skins.ClothPhysics;
using MGFR.StructuredVoiceFinal;
namespace MGFR.Repairs {
 public sealed class ClothScaleReview:MonoBehaviour {
  [Serializable]class Sample {public float scale,clothHeightRatio,clothWidthRatio,meanConstraintStrain,maxConstraintStrain;public bool finite,detachedFollows;}
  [Serializable]class Result {public bool pass;public Sample[] samples;public string mode="Actual player, live XPBD cloth and detached garment; uniform 0.2 to 4 character scale, no headset";}
  IEnumerator Start(){
   AudioListener.volume=0;var auto=FindAnyObjectByType<AutomaticVoiceSession>();if(auto!=null)auto.enabled=false;var args=Environment.GetCommandLineArgs();string output=args[Array.IndexOf(args,"-mgfr-scale-review-out")+1];
   SiSkinSwitcher skins;SwimsuitClothRuntime cloth;MainAvatarActions driver;MGFR.Wardrobe.WardrobeLiveRuntime wardrobe;
   float deadline=Time.realtimeSinceStartup+45;
   while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||(cloth=FindAnyObjectByType<SwimsuitClothRuntime>())==null||!cloth.IsReady||(driver=FindAnyObjectByType<MainAvatarActions>())==null||!driver.Ready||(wardrobe=FindAnyObjectByType<MGFR.Wardrobe.WardrobeLiveRuntime>())==null||!wardrobe.IsReady){if(Time.realtimeSinceStartup>deadline){Application.Quit(2);yield break;}yield return null;}
   driver.ReviewOverride=true;driver.enabled=false;var animation=skins.Loader.GetComponent<Animation>();animation.enabled=false;
   var control=skins.Loader.GetComponent<SiCharacterController>();if(control==null)control=FindAnyObjectByType<SiCharacterController>();
   var rows=new List<Sample>();var originalPosition=control.PlanarPosition;float originalYaw=control.Yaw,ground=control.GroundHeight;
   GameObject detached;string reason;if(!wardrobe.Adapter.TryDetach("shoe_left",out detached,out reason))throw new Exception("Scale review detach failed");
   foreach(float scale in new[]{1f,.5f,.2f,2f,4f,1f}){
    control.RestoreRoomPlacement(originalPosition,originalYaw,scale,ground);yield return new WaitForSeconds(.6f);
    var clothRenderer=GameObject.Find("Simulated swimsuit cloth").GetComponent<MeshRenderer>();var bounds=clothRenderer.bounds;
    var row=new Sample{scale=scale,clothHeightRatio=bounds.size.y/scale,clothWidthRatio=bounds.size.x/scale,finite=true,detachedFollows=Mathf.Abs(detached.transform.lossyScale.x-skins.Loader.transform.lossyScale.x)<.0001f};
    foreach(var p in cloth.Solver.Particles)row.finite&=float.IsFinite(p.position.x)&&float.IsFinite(p.position.y)&&float.IsFinite(p.position.z);
    // Measure the existing solver's real link constraints at the current body scale.
    var flags=System.Reflection.BindingFlags.Instance|System.Reflection.BindingFlags.NonPublic;
    var links=(System.Collections.IList)typeof(SwimsuitClothSolver).GetField("links",flags).GetValue(cloth.Solver);float reference=(float)typeof(SwimsuitClothSolver).GetField("scale",flags).GetValue(cloth.Solver);
    foreach(var link in links){var t=link.GetType();int a=(int)t.GetField("a").GetValue(link),b=(int)t.GetField("b").GetValue(link);float rest=(float)t.GetField("rest").GetValue(link)*scale/reference;float strain=Mathf.Abs(Vector3.Distance(cloth.Solver.Particles[a].position,cloth.Solver.Particles[b].position)-rest)/Mathf.Max(rest,.00001f);row.meanConstraintStrain+=strain;row.maxConstraintStrain=Mathf.Max(row.maxConstraintStrain,strain);}
    row.meanConstraintStrain/=links.Count;rows.Add(row);
   }
   var result=new Result{pass=true,samples=rows.ToArray()};float h=rows[0].clothHeightRatio,w=rows[0].clothWidthRatio;
   foreach(var row in rows)result.pass&=row.finite&&row.detachedFollows&&Mathf.Abs(row.clothHeightRatio/h-1)<.12f&&Mathf.Abs(row.clothWidthRatio/w-1)<.12f&&row.meanConstraintStrain<.35f;
   using(var stream=new FileStream(output,FileMode.CreateNew))using(var writer=new StreamWriter(stream))writer.Write(JsonUtility.ToJson(result,true));Debug.Log("MGFR_CLOTH_SCALE_"+(result.pass?"PASS":"FAIL"));Application.Quit(result.pass?0:5);
  }
 }
}
