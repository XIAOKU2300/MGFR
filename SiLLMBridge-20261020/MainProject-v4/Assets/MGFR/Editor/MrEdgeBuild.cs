using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
public static class MrEdgeBuild
{
    public static void Build()
    {
        PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone, ScriptingImplementation.Mono2x);
        MGFR.EditorTools.MgfrEditorMenu.EnsureAlwaysIncludedShader("MGFR/Character");
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = new[] { "Assets/MGFR/Scenes/SiCharacter.unity" },
            target = BuildTarget.StandaloneWindows64, locationPathName = "Build/Windows/MGFR.exe",
            options = BuildOptions.Development });
        Debug.Log($"[MR edge build] {report.summary.result} errors={report.summary.totalErrors} warnings={report.summary.totalWarnings}");
        EditorApplication.Exit(report.summary.result == BuildResult.Succeeded && report.summary.totalErrors == 0 ? 0 : 1);
    }
}
