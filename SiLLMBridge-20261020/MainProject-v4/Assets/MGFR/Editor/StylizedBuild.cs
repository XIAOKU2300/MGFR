using UnityEditor;
using MGFR.EditorTools;
namespace MGFR.Rendering
{
 public static class StylizedBuild
 {
  [MenuItem("MGFR/Build/Stylized Windows Player (Mono)",priority=63)]
  public static void Build()
  {
   var result=MgfrEditorMenu.EnsureAlwaysIncludedShader("MGFR/StylizedCharacter");
   UnityEngine.Debug.Log("[MGFR render build] "+result);
   AssetDatabase.SaveAssets();MgfrBuild.PlayerMono();
  }
 }
}
