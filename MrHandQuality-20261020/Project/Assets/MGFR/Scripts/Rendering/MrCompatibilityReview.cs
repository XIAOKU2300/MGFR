using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Skins;
using MGFR.StructuredVoiceFinal;

namespace MGFR.Rendering
{
    public sealed class MrCompatibilityReview:MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-quality-compat-review")>=0)new GameObject("Latest source compatibility review").AddComponent<MrCompatibilityReview>();}
        IEnumerator Start()
        {
            float end=Time.realtimeSinceStartup+45;SiSkinSwitcher skins;MainAvatarActions actions;
            while((skins=FindAnyObjectByType<SiSkinSwitcher>())==null||!skins.IsReady||(actions=FindAnyObjectByType<MainAvatarActions>())==null||!actions.Ready)
            {if(Time.realtimeSinceStartup>end){Application.Quit(2);yield break;}yield return null;}
            var checks=new List<string>();bool pass=true;
            void Check(string label,bool ok){checks.Add(label+"="+ok);pass&=ok;}
            Check("latestDirectionIKAndActionGuard",actions.IsReviewedAction("wave")&&!actions.IsReviewedAction("walk"));
            var guard=FindAnyObjectByType<MrChromaEdgeGuard>();
            foreach(string skin in new[]{"original","swimsuit","original","swimsuit"})
            {
                Check("switch-"+skin,skins.TrySelect(skin));yield return null;guard.Refresh();
                foreach(bool style in new[]{false,true})
                {
                    skins.Style.SetActive(style);guard.Refresh();
                    var mats=skins.Loader.Renderer.sharedMaterials;
                    Check(skin+"-"+style+"-bodyDepth",mats[7].GetFloat("_ZWrite")==1);
                    Check(skin+"-"+style+"-sheerClothPreserved",mats[10].GetFloat("_ZWrite")==0&&mats[10].GetFloat("_DstBlend")!=0);
                    Check(skin+"-"+style+"-coverageActive",MrMaterialPolicy.Active&&mats[12].GetFloat("_MrCoverage")==1);
                }
            }
            guard.SetRequested(false);Check("comparisonRestoresTransparentClothing",skins.Loader.Renderer.sharedMaterials[8].GetFloat("_DstBlend")!=0);
            guard.SetRequested(true);Check("comparisonReapplies",MrMaterialPolicy.Active);
            var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-quality-output");Directory.CreateDirectory(args[at+1]);File.WriteAllLines(Path.Combine(args[at+1],"compatibility-checks.txt"),checks);
            Debug.Log("MR_COMPATIBILITY_REVIEW "+string.Join(" ",checks)+" PASS="+pass);Application.Quit(pass?0:1);
        }
    }
}
