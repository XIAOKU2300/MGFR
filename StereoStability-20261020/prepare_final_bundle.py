from pathlib import Path
root=Path(__file__).resolve().parent
project=root/'ShaderProject-retained'
menu=root.parent/'DialogueRenderRepair-20261020/Final-v3/Source/GesturePanel'
for name in ('GesturePanel.shader','GesturePanelText.shader'):
    text=(menu/name).read_text(encoding='utf-8').replace('#pragma multi_compile _ STEREO_INSTANCING_ON','#pragma multi_compile _ STEREO_INSTANCING_ON\n#pragma multi_compile _ MGFR_BUILD_STEREO_VARIANT')
    with (project/'Assets'/name).open('x',encoding='utf-8') as f:f.write(text)
path=project/'Assets/Editor/StereoVariantAudit.cs'
text=path.read_text(encoding='utf-8').replace('Bundle-retained-v2','Bundle-final')
text=text.replace('new[]{new AssetBundleBuild{assetBundleName="mgfr-mr-coverage",assetNames=names}}','new[]{new AssetBundleBuild{assetBundleName="mgfr-mr-coverage",assetNames=names.Where(n=>!n.StartsWith("Assets/GesturePanel")).ToArray()},new AssetBundleBuild{assetBundleName="gesture-touch-panel-v1",assetNames=names.Where(n=>n.StartsWith("Assets/GesturePanel")).ToArray()}}')
text=text.replace('Debug.Log("STEREO_BUNDLE_AUDIT_DONE");','''
  var audit=File.ReadAllLines(Path.Combine(output,"variant-audit.txt"));
  foreach(var row in audit){if(!row.Contains("STEREO_INSTANCING_ON")||row.Contains("MGFR_BUILD_STEREO_VARIANT"))throw new Exception("Stereo variant retention failed: "+row.Split('|')[0]);}
  if(audit.Length<24)throw new Exception("Incomplete shader audit");
  Debug.Log("STEREO_BUNDLE_AUDIT_DONE checkedPassStages="+audit.Length);''')
path.write_text(text,encoding='utf-8')
source=(root/'GpuProbe-v1/Assets/Editor/StereoGpuProbeV4.cs').read_text(encoding='utf-8').replace('StereoGpuProbeV4','StereoGpuProbeFinal').replace('Probe-retained-v2','Probe-final').replace('Bundle-retained-v2','Bundle-final')
source=source.replace('var rows=new List<Row>();','var menuBundle=AssetBundle.LoadFromFile("H:/MGFR/StereoStability-20261020/Bundle-final/gesture-touch-panel-v1");var rows=new List<Row>();')
source=source.replace('foreach(var shader in bundle.LoadAllAssets<Shader>()){','foreach(var shader in bundle.LoadAllAssets<Shader>().Concat(menuBundle.LoadAllAssets<Shader>())){')
with (root/'GpuProbe-v1/Assets/Editor/StereoGpuProbeFinal.cs').open('x',encoding='utf-8') as f:f.write(source)
print('Prepared full active-runtime stereo shader set and build gates.')
