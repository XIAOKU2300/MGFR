using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class ZmdRenderBuild
{
 public static void Capture()
 {EditorSceneManager.OpenScene("Assets/MGFR/Scenes/SiCharacter.unity");EditorApplication.EnterPlaymode();}
 public static void Build()
 {
  PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
  MGFR.EditorTools.MgfrEditorMenu.EnsureAlwaysIncludedShader("MGFR/Character");
  MGFR.EditorTools.MgfrEditorMenu.EnsureAlwaysIncludedShader("MGFR/StylizedCharacter");
  foreach(string kind in new[]{"Face","Skin","Cloth","Hair"})MGFR.EditorTools.MgfrEditorMenu.EnsureAlwaysIncludedShader("MGFR/ZmdEndfield/"+kind);
  AssetDatabase.SaveAssets();
  var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/MGFR/Scenes/SiCharacter.unity"},target=BuildTarget.StandaloneWindows64,locationPathName="Build/Windows/MGFR.exe",options=BuildOptions.Development});
  Debug.Log($"[ZMD build] {result.summary.result} errors={result.summary.totalErrors} warnings={result.summary.totalWarnings}");EditorApplication.Exit(result.summary.result==BuildResult.Succeeded?0:1);
 }
}
