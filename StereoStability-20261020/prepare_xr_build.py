from pathlib import Path
import shutil,json
root=Path(__file__).resolve().parent
project=root/'ShaderProject-v1'
base=root.parent/'HandCoexist-20261019/Project'
shutil.copytree(base/'Assets/XR',project/'Assets/XR',dirs_exist_ok=True)
shutil.copyfile(base/'ProjectSettings/EditorBuildSettings.asset',project/'ProjectSettings/EditorBuildSettings.asset')
packages=('com.unity.inputsystem@7a4e1a2a8194','com.unity.xr.core-utils@a8b900321199','com.unity.xr.legacyinputhelpers@9535ff2c27ac','com.unity.xr.management@2ad85c7dd480','com.unity.xr.openxr@b5b77b4027be')
manifest=json.loads((project/'Packages/manifest.json').read_text(encoding='utf-8-sig'))
for name in packages:
    source=base/'Library/PackageCache'/name
    target=project/'Packages'/name.split('@')[0]
    shutil.copytree(source,target,dirs_exist_ok=True)
    package=json.loads((target/'package.json').read_text(encoding='utf-8-sig'))
    manifest['dependencies'][package['name']]=package['version']
for module in ('xr','vr','subsystems','physics','ui','imgui','jsonserialize'):
    manifest['dependencies']['com.unity.modules.'+module]='1.0.0'
(project/'Packages/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
script=(project/'Assets/Editor/StereoVariantAudit.cs').read_text(encoding='utf-8')
script=script[script.index('public static class StereoBundleAudit'):]
script='using System;using System.IO;using System.Linq;using UnityEditor;using UnityEditor.Rendering;using UnityEngine;using UnityEngine.Rendering;\n'+script
script=script.replace('StereoBundleAudit','StereoBundleXr').replace('Bundle-audit-baseline','Bundle-xr-v1')
script=script.replace('AssetDatabase.Refresh();','''AssetDatabase.Refresh();
  GraphicsSettings.SetShaderMode(BuiltinShaderType.DeferredShading,BuiltinShaderMode.UseBuiltin);
  var general=UnityEditor.XR.Management.XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.Standalone);
  if(general==null||general.Manager==null||general.Manager.activeLoaders.Count==0)throw new Exception("XR loader not configured");
  UnityEngine.XR.OpenXR.OpenXRSettings.GetSettingsForBuildTargetGroup(BuildTargetGroup.Standalone).renderMode=UnityEngine.XR.OpenXR.OpenXRSettings.RenderMode.SinglePassInstanced;
  Debug.Log("XR_SHADER_BUILD_LOADER "+general.Manager.activeLoaders[0].name);''')
with (project/'Assets/Editor/StereoBundleXr.cs').open('x',encoding='utf-8') as f:f.write(script)
print('Prepared cached OpenXR packages and actual XR build settings.')
