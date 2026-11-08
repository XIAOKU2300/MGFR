from pathlib import Path
import shutil
root=Path(__file__).resolve().parent
source=root.parent/'DialogueRenderRepair-20261020/ShaderProject-v4'
project=root/'ShaderProject-retained'
project.mkdir()
for name in ('Assets','Packages','ProjectSettings'):
    shutil.copytree(source/name,project/name)
audit=(root/'ShaderProject-v1/Assets/Editor/StereoVariantAudit.cs').read_text(encoding='utf-8')
audit=audit.replace('StereoBundleAudit','StereoRetainedBundle').replace('Bundle-audit-baseline','Bundle-retained-v1')
with (project/'Assets/Editor/StereoVariantAudit.cs').open('x',encoding='utf-8') as f:f.write(audit)
retain=r'''using System.Collections.Generic;using UnityEditor.Build;using UnityEditor.Rendering;using UnityEngine;using UnityEngine.Rendering;
// The isolated bundle builder has no XR loader. Reinsert the engine's own
// stereo keyword after its automatic pre-strip, before compiling the bundle.
public sealed class KeepStereoRepairVariants:IPreprocessShaders {
 public int callbackOrder=>int.MinValue;
 public void OnProcessShader(Shader shader,ShaderSnippetData snippet,IList<ShaderCompilerData> data){
  if(!shader.name.StartsWith("MGFR/"))return;
  var keyword=new ShaderKeyword("STEREO_INSTANCING_ON");
  int count=data.Count;
  for(int i=0;i<count;i++){
   var stereo=data[i];if(stereo.shaderKeywordSet.IsEnabled(keyword))continue;
   stereo.shaderKeywordSet.Enable(keyword);data.Add(stereo);
  }
 }
}
'''
with (project/'Assets/Editor/KeepStereoRepairVariants.cs').open('x',encoding='utf-8') as f:f.write(retain)
print(project)
