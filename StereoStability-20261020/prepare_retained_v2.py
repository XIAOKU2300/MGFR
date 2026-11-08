from pathlib import Path
root=Path(__file__).resolve().parent
project=root/'ShaderProject-retained'
for path in (project/'Assets').rglob('*.shader'):
    text=path.read_text(encoding='utf-8')
    text=text.replace('#pragma multi_compile _ STEREO_INSTANCING_ON','#pragma multi_compile _ STEREO_INSTANCING_ON\n#pragma multi_compile _ MGFR_BUILD_STEREO_VARIANT')
    path.write_text(text,encoding='utf-8')
path=project/'Assets/Editor/KeepStereoRepairVariants.cs'
path.write_text(r'''using System.Collections.Generic;using UnityEditor.Build;using UnityEditor.Rendering;using UnityEngine;using UnityEngine.Rendering;
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
''',encoding='utf-8')
path=project/'Assets/Editor/StereoVariantAudit.cs'
path.write_text(path.read_text(encoding='utf-8').replace('Bundle-retained-v1','Bundle-retained-v2'),encoding='utf-8')
source=(root/'GpuProbe-v1/Assets/Editor/StereoGpuProbeV3.cs').read_text(encoding='utf-8')
source=source.replace('StereoGpuProbeV3','StereoGpuProbeV4').replace('Probe-baseline-v3','Probe-retained-v2')
source=source.replace('H:/MGFR/DialogueRenderRepair-20261020/Final-v3/Player/MGFR_Data/StreamingAssets/mgfr-mr-coverage','H:/MGFR/StereoStability-20261020/Bundle-retained-v2/mgfr-mr-coverage')
source=source.replace('command.DrawMeshInstanced(mesh,0,material,0,new[]{Matrix4x4.identity,Matrix4x4.identity},2);','command.SetInstanceMultiplier(2);command.DrawMesh(mesh,Matrix4x4.identity,material,0,0);command.SetInstanceMultiplier(1);')
with (root/'GpuProbe-v1/Assets/Editor/StereoGpuProbeV4.cs').open('x',encoding='utf-8') as f:f.write(source)
print('Prepared separate mono and native stereo build variants.')
