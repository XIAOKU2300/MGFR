using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
public static class BuildRepairShaders {
 public static void Run(){
  PlayerSettings.colorSpace=ColorSpace.Linear;
  PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false);
  PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{UnityEngine.Rendering.GraphicsDeviceType.Direct3D11});
  PlayerSettings.stereoRenderingPath=StereoRenderingPath.Instancing;
  AssetDatabase.Refresh();
  var names=AssetDatabase.FindAssets("t:Shader").Select(AssetDatabase.GUIDToAssetPath).ToArray();
  foreach(var name in names){var shader=AssetDatabase.LoadAssetAtPath<Shader>(name);foreach(var message in ShaderUtil.GetShaderMessages(shader))if(message.severity.ToString()=="Error")throw new Exception("Repair shader compile failed: "+name+" "+message.message);}
  string output=Path.Combine(Directory.GetParent(Application.dataPath).Parent.FullName,"ShaderBundle-v3");
  if(Directory.Exists(output))throw new Exception("Bundle output exists");Directory.CreateDirectory(output);StereoVariantAudit.Output=output;
  var result=BuildPipeline.BuildAssetBundles(output,new[]{new AssetBundleBuild{assetBundleName="mgfr-mr-coverage",assetNames=names}},BuildAssetBundleOptions.ForceRebuildAssetBundle,BuildTarget.StandaloneWindows64);
  if(result==null)throw new Exception("Bundle failed");
  foreach(var name in names){var shader=AssetDatabase.LoadAssetAtPath<Shader>(name);foreach(var message in ShaderUtil.GetShaderMessages(shader))if(message.severity.ToString()=="Error")throw new Exception("Repair shader variant failed: "+name+" "+message.message);}
  using(var stream=new FileStream(Path.Combine(output,"shader-checks.txt"),FileMode.CreateNew))using(var writer=new StreamWriter(stream))writer.WriteLine("Compiled repair shaders: "+names.Length);
  var audit=File.ReadAllLines(Path.Combine(output,"variant-audit.txt"));
  foreach(var row in audit){var variants=row.Split('|')[4].Split(';');if(!variants.Any(v=>v.Contains("STEREO_INSTANCING_ON"))||!variants.Any(v=>!v.Contains("STEREO_INSTANCING_ON"))||row.Contains("MGFR_BUILD_STEREO_VARIANT"))throw new Exception("Mono/stereo variant retention failed");}
  if(audit.Select(r=>r.Split('|')[0].Trim()).Distinct().Count()!=names.Length)throw new Exception("Incomplete variant audit");
  Debug.Log("MGFR_REPAIR_SHADER_BUNDLE_PASS count="+names.Length);
 }
}
