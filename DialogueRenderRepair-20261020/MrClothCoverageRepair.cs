using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Character;
namespace MGFR.Repairs {
 [DefaultExecutionOrder(31980)] public sealed class MrClothCoverageRepair:MonoBehaviour {
  readonly Dictionary<string,Shader> variants=new Dictionary<string,Shader>();
  readonly HashSet<Material> changed=new HashSet<Material>();
  AssetBundle bundle;float nextScan;public int ChangedMaterials=>changed.Count;
  public bool Ready {get;private set;}
  public static void Install(){if(FindAnyObjectByType<MrClothCoverageRepair>()==null)new GameObject("MR transparency repair").AddComponent<MrClothCoverageRepair>();}
  void Start(){
   string file=Path.Combine(Application.streamingAssetsPath,"mgfr-mr-coverage");
   bundle=AssetBundle.LoadFromFile(file);if(bundle==null)throw new InvalidOperationException("MR repair shader bundle missing");
   foreach(var shader in bundle.LoadAllAssets<Shader>()){
    if(!shader.isSupported)throw new InvalidOperationException("MR repair shader unsupported: "+shader.name);
    const string suffix="/MrCoverage";if(shader.name.EndsWith(suffix,StringComparison.Ordinal))variants.Add(shader.name.Substring(0,shader.name.Length-suffix.Length),shader);
   }
   var subtitle=bundle.LoadAsset<Shader>("Assets/Subtitle/ChatOverlayChroma.shader");
   if(subtitle==null)throw new InvalidOperationException("Subtitle repair shader missing");
   SubtitleChromaRepair.Install(subtitle);Shader.SetGlobalFloat("_MGFRRgbKeyCoverageCell",2);
   Ready=true;Debug.Log("MGFR_MR_REPAIR_READY variants="+variants.Count);
  }
  void LateUpdate(){if(!Ready||Time.unscaledTime<nextScan)return;nextScan=Time.unscaledTime+.2f;RefreshMaterials();}
  public void RefreshMaterials(){
   foreach(var renderer in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude,FindObjectsSortMode.None))foreach(var material in renderer.sharedMaterials){
    if(material==null||changed.Contains(material)||!variants.TryGetValue(material.shader.name,out var shader))continue;
    // Transparent body/cloth variants only; preserve face/hair and opaque shading.
    if(!material.HasProperty("_SrcBlend")||material.GetFloat("_SrcBlend")<4.5f)continue;
    int queue=material.renderQueue;material.shader=shader;material.renderQueue=queue;changed.Add(material);
   }
  }
 }
}
