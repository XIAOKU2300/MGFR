using UnityEditor;
using UnityEditor.XR.OpenXR.Features;
using UnityEngine;
using UnityEngine.XR.Hands.OpenXR;
using UnityEngine.XR.OpenXR;
using MGFR.Rendering;

namespace MGFR.BareHands
{
 public static class HandsBuild
 {
  [MenuItem("MGFR/Build/Bare hands Windows Player (Mono)",priority=64)]
  public static void Build()
  {
   FeatureHelpers.RefreshFeatures(BuildTargetGroup.Standalone);
   var settings=OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Standalone);
   var feature=settings.GetFeature<HandTracking>();feature.enabled=true;
   EditorUtility.SetDirty(settings);AssetDatabase.SaveAssets();
   Debug.Log("[MGFR hands build] Hand Tracking Subsystem enabled="+feature.enabled+"; XR Hands 1.8.1 embedded official package");
   StylizedBuild.Build();
  }
 }
}
