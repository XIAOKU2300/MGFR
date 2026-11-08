using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
public static class SwimsuitClothBuild
{
    public static void Build()
    {
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
        MGFR.EditorTools.MgfrEditorMenu.EnsureAlwaysIncludedShader("MGFR/Character");
        var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/MGFR/Scenes/SiCharacter.unity"},
            target=BuildTarget.StandaloneWindows64,locationPathName="Build/Windows/MGFR.exe",options=BuildOptions.Development});
        Debug.Log($"[Swimsuit cloth build] {result.summary.result} errors={result.summary.totalErrors} warnings={result.summary.totalWarnings}");
        EditorApplication.Exit(result.summary.result==BuildResult.Succeeded&&result.summary.totalErrors==0?0:1);
    }
}
