using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;
public static class BridgeBuild {
 static string Arg(string key){var a=Environment.GetCommandLineArgs();return a[Array.IndexOf(a,key)+1];}
 public static void Run(){try{
  string dest=Arg("-playerOut");if(Directory.Exists(dest))throw new Exception("Player output exists");Directory.CreateDirectory(dest);
  EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);new GameObject("Si LLM bridge").AddComponent<BridgeCharacter>();
  Directory.CreateDirectory("Assets/Resources");if(File.Exists("Assets/Bridge.unity")||File.Exists("Assets/Resources/NativeShader.mat"))throw new Exception("Build assets exist");
  AssetDatabase.CreateAsset(new Material(Shader.Find("EndfieldNative/Preview")),"Assets/Resources/NativeShader.mat");EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),"Assets/Bridge.unity");
  PlayerSettings.productName="Si LLM Motion Bridge";PlayerSettings.companyName="Local Native Preview";PlayerSettings.defaultScreenWidth=1400;PlayerSettings.defaultScreenHeight=1000;PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.runInBackground=true;PlayerSettings.colorSpace=ColorSpace.Gamma;
  PlayerSettings.SetScriptingBackend(UnityEditor.Build.NamedBuildTarget.Standalone,ScriptingImplementation.Mono2x);PlayerSettings.SetManagedStrippingLevel(UnityEditor.Build.NamedBuildTarget.Standalone,ManagedStrippingLevel.Disabled);
  PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false);PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{GraphicsDeviceType.Direct3D11});
  var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/Bridge.unity"},locationPathName=Path.Combine(dest,"SiLLMPlayer.exe"),target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
  if(result.summary.result!=BuildResult.Succeeded)throw new Exception("Build failed");Debug.Log("SI_BRIDGE_BUILD_PASS "+result.summary.totalSize);EditorApplication.Exit(0);
 }catch(Exception e){Debug.LogException(e);EditorApplication.Exit(1);}}
}
