from pathlib import Path
import shutil
root=Path(__file__).resolve().parent
source=root.parent/'DialogueRenderRepair-20261020/ShaderProject-v4'
project=root/'ShaderProject-v1'
project.mkdir()
for name in ('Assets','Packages','ProjectSettings'):
    shutil.copytree(source/name,project/name)
editor=project/'Assets/Editor'
script=r'''using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Rendering;
using UnityEngine;
using UnityEngine.Rendering;
public class StereoVariantAudit:IPreprocessShaders {
 public int callbackOrder=>int.MaxValue;
 public static string Output;
 public void OnProcessShader(Shader shader, ShaderSnippetData snippet,IList<ShaderCompilerData> data){
  if(Output==null||!shader.name.StartsWith("MGFR/"))return;
  var keywords=data.Select(d=>string.Join(" ",d.shaderKeywordSet.GetShaderKeywords().Select(k=>k.name).OrderBy(k=>k))).Distinct().ToArray();
  File.AppendAllText(Path.Combine(Output,"variant-audit.txt"),shader.name+" | "+snippet.passName+" | "+snippet.shaderType+" | "+data.Count+" | "+string.Join(";",keywords)+"\n");
 }
}
public static class StereoBundleAudit {
 public static void Run(){
  PlayerSettings.colorSpace=ColorSpace.Linear;
  PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64,false);
  PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64,new[]{GraphicsDeviceType.Direct3D11});
  PlayerSettings.stereoRenderingPath=StereoRenderingPath.Instancing;
  AssetDatabase.Refresh();
  string output=Path.Combine(Directory.GetParent(Application.dataPath).Parent.FullName,"Bundle-audit-baseline");
  if(Directory.Exists(output))throw new Exception("Output exists");Directory.CreateDirectory(output);StereoVariantAudit.Output=output;
  var names=AssetDatabase.FindAssets("t:Shader").Select(AssetDatabase.GUIDToAssetPath).ToArray();
  foreach(var path in names){var shader=AssetDatabase.LoadAssetAtPath<Shader>(path);var pass=ShaderUtil.GetShaderData(shader).GetSubshader(0).GetPass(0);
   var variant=pass.PreprocessVariant(ShaderType.Vertex,new[]{"STEREO_INSTANCING_ON"},ShaderCompilerPlatform.D3D,BuildTarget.StandaloneWindows64,true);
   File.WriteAllText(Path.Combine(output,shader.name.Replace('/','_')+".hlsl"),variant.PreprocessedCode);
  }
  var result=BuildPipeline.BuildAssetBundles(output,new[]{new AssetBundleBuild{assetBundleName="mgfr-mr-coverage",assetNames=names}},BuildAssetBundleOptions.ForceRebuildAssetBundle,BuildTarget.StandaloneWindows64);
  if(result==null)throw new Exception("Build failed");
  Debug.Log("STEREO_BUNDLE_AUDIT_DONE");
 }
}
'''
with (editor/'StereoVariantAudit.cs').open('x',encoding='utf-8') as f:f.write(script)
print(project)
