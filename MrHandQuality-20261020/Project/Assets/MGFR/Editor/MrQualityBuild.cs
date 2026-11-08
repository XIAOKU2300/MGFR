using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace MGFR.Editor
{
    public static class MrQualityBuild
    {
        public static void Run()
        {
            try
            {
                var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mr-output");
                if(at<0||at+1>=args.Length)throw new InvalidOperationException("Missing output");
                string output=Path.GetFullPath(args[at+1]);if(Directory.Exists(output))throw new InvalidOperationException("Build output already exists; choose a new directory");
                PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
                PlayerSettings.companyName="MGFR";PlayerSettings.productName="MGFR";
                PlayerSettings.runInBackground=true;
                PlayerSettings.SetStackTraceLogType(LogType.Log,StackTraceLogType.None);
                var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/MGFR/Scenes/SiCharacter.unity"},locationPathName=Path.Combine(output,"MGFR.exe"),target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
                if(report.summary.result!=BuildResult.Succeeded||report.summary.totalErrors!=0)throw new InvalidOperationException("Candidate build failed");
                Debug.Log("MR_QUALITY_BUILD_PASS "+MGFR.Rendering.MrQualityDiagnostics.BuildId+" bytes="+report.summary.totalSize);EditorApplication.Exit(0);
            }
            catch(Exception e){Debug.LogError("MR_QUALITY_BUILD_FAILED "+e.GetType().Name+": "+e.Message);EditorApplication.Exit(1);}
        }
    }
}
