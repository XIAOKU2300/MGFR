using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;
namespace MGFR.StructuredActions {
 public static class MainProjectBuild {
  public static void Run(){try{
   var args=Environment.GetCommandLineArgs();string output=args[Array.IndexOf(args,"-mainOut")+1];if(Directory.Exists(output))throw new Exception("Output exists");Directory.CreateDirectory(output);
   PlayerSettings.SetScriptingBackend(NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);
   var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/MGFR/Scenes/SiCharacter.unity"},locationPathName=Path.Combine(output,"MGFR.exe"),target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
   if(report.summary.result!=BuildResult.Succeeded)throw new Exception("Main project build failed");Debug.Log("MGFR_MAIN_ACTION_BUILD_PASS "+report.summary.totalSize);EditorApplication.Exit(0);
  }catch(Exception e){Debug.LogException(e);EditorApplication.Exit(1);}}
 }
}
