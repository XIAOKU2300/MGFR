using System.Collections.Generic;using UnityEditor.Build;using UnityEditor.Rendering;using UnityEngine;using UnityEngine.Rendering;
// A build-only marker makes two independently allocated keyword sets survive
// the engine's XR pre-strip. Canonicalize the marked set to the native keyword.
// Runtime cameras continue selecting STEREO_INSTANCING_ON normally.
public sealed class KeepStereoRepairVariants:IPreprocessShaders {
 public int callbackOrder=>int.MinValue;
 public void OnProcessShader(Shader shader,ShaderSnippetData snippet,IList<ShaderCompilerData> data){
  if(!shader.name.StartsWith("MGFR/"))return;
  var marker=new ShaderKeyword("MGFR_BUILD_STEREO_VARIANT");
  var stereo=new ShaderKeyword("STEREO_INSTANCING_ON");
  for(int i=0;i<data.Count;i++){
   var variant=data[i];if(!variant.shaderKeywordSet.IsEnabled(marker))continue;
   variant.shaderKeywordSet.Disable(marker);variant.shaderKeywordSet.Enable(stereo);data[i]=variant;
  }
 }
}
