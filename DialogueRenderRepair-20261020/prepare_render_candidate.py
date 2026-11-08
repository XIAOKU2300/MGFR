"""Prepare an independent shader project and module sources, preserving all originals."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE = ROOT / 'HandCoexist-20261019/Project'
PROJECT = HERE / 'ShaderProject-v1'
PROJECT.mkdir(exist_ok=False)

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data.encode('utf-8') if isinstance(data, str) else data)

write(PROJECT / 'Packages/manifest.json', json.dumps({'dependencies': {'com.unity.modules.assetbundle': '1.0.0', 'com.unity.modules.imageconversion': '1.0.0'}}))
write(PROJECT / 'ProjectSettings/ProjectVersion.txt', 'm_EditorVersion: 6000.3.26f1\n')
common = '''#ifndef MGFR_COVERAGE_INCLUDED
#define MGFR_COVERAGE_INCLUDED
float _MGFRRgbKeyCoverage;
float _MGFRRgbKeyCoverageCell;
float MgfrCoverageAlpha(float alpha, float2 pixel)
{
    if (_MGFRRgbKeyCoverage < .5) return alpha;
    // Align each 2x2 coverage cell to the encoder's 4:2:0 chroma samples.
    // Fixed spatial coverage avoids time noise and never mixes in key green.
    uint2 p = (uint2)floor(pixel / max(2, _MGFRRgbKeyCoverageCell));
    const float bayer[16] = {0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5};
    float threshold = (bayer[(p.y & 3) * 4 + (p.x & 3)] + .5) / 16;
    clip(saturate(alpha) - threshold);
    return 1;
}
#endif
'''
write(PROJECT / 'Assets/RepairCoverage.cginc', common)
paths = [
    'Assets/MGFR/Shaders/MgfrCharacter.shader',
    'Assets/MGFR/Resources/MgfrStylized.shader',
    'Assets/MGFR/Resources/MgfrEndfieldClothing.shader',
    'Assets/MGFR/Skins/Resources/SiSwimsuitCloth.shader',
    'Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield/ZmdCloth.shader',
]
for name in paths:
    source = (BASE / name).read_text(encoding='utf-8')
    first = source.index('"', source.index('Shader ')) + 1
    last = source.index('"', first)
    source = source[:last] + '/MrCoverage' + source[last:]
    if 'Zmd' in name or 'SiSwimsuitCloth' in name:
        source = source.replace('HLSLPROGRAM', 'HLSLPROGRAM\n#include "Assets/RepairCoverage.cginc"', 1)
        old, new = 'return half4(ZmdFinish(finalColor),alpha);', 'return half4(ZmdFinish(finalColor),MgfrCoverageAlpha(alpha,i.positionCS.xy));'
    elif 'MgfrCharacter' in name:
        source = source.replace('#include "UnityCG.cginc"', '#include "UnityCG.cginc"\n#include "Assets/RepairCoverage.cginc"')
        old, new = 'return fixed4(lit, c.a);', 'return fixed4(lit, MgfrCoverageAlpha(c.a,i.pos.xy));'
    else:
        source = source.replace('#include "UnityCG.cginc"', '#include "UnityCG.cginc"\n#include "Assets/RepairCoverage.cginc"')
        old, new = 'return float4(color,base.a);', 'return float4(color,MgfrCoverageAlpha(base.a,i.pos.xy));'
        source = source.replace('return float4(_OutlineTint.rgb,_OutlineTint.a);', 'return float4(_OutlineTint.rgb,MgfrCoverageAlpha(_OutlineTint.a,i.pos.xy));')
    assert source.count(old) == 1, name
    write(PROJECT / name, source.replace(old, new))
includes = BASE / 'Assets/MGFR/RenderStyles/ZmdEndfield/Resources/ZmdEndfield'
for path in includes.glob('*.cginc'):
    write(PROJECT / path.relative_to(BASE), path.read_bytes())
write(PROJECT / 'Assets/Editor/BuildRepairShaders.cs', r'''using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
public static class BuildRepairShaders {
 public static void Run(){
  AssetDatabase.Refresh();
  var names=AssetDatabase.FindAssets("t:Shader").Select(AssetDatabase.GUIDToAssetPath).ToArray();
  foreach(var name in names){var shader=AssetDatabase.LoadAssetAtPath<Shader>(name);foreach(var message in ShaderUtil.GetShaderMessages(shader))if(message.severity.ToString()=="Error")throw new Exception("Repair shader compile failed: "+name+" "+message.message);}
  string output=Path.Combine(Directory.GetParent(Application.dataPath).Parent.FullName,"ShaderBundle-v1");
  if(Directory.Exists(output))throw new Exception("Bundle output exists");Directory.CreateDirectory(output);
  var result=BuildPipeline.BuildAssetBundles(output,new[]{new AssetBundleBuild{assetBundleName="mgfr-mr-coverage",assetNames=names}},BuildAssetBundleOptions.ForceRebuildAssetBundle,BuildTarget.StandaloneWindows64);
  if(result==null)throw new Exception("Bundle failed");
  foreach(var name in names){var shader=AssetDatabase.LoadAssetAtPath<Shader>(name);foreach(var message in ShaderUtil.GetShaderMessages(shader))if(message.severity.ToString()=="Error")throw new Exception("Repair shader variant failed: "+name+" "+message.message);}
  using(var stream=new FileStream(Path.Combine(output,"shader-checks.txt"),FileMode.CreateNew))using(var writer=new StreamWriter(stream))writer.WriteLine("Compiled repair shaders: "+names.Length);
  Debug.Log("MGFR_REPAIR_SHADER_BUNDLE_PASS count="+names.Length);
 }
}
''')
print('NEW_SHADER_PROJECT', PROJECT)
