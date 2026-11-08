using System;
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
