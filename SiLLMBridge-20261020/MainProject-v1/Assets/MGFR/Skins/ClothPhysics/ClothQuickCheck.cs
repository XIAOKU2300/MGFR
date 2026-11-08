using System;
using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Skins;

namespace MGFR.Skins.ClothPhysics
{
    public sealed class ClothQuickCheck : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-cloth-check")>=0)new GameObject("Cloth quick check").AddComponent<ClothQuickCheck>();}
        IEnumerator Start()
        {
            float deadline=Time.realtimeSinceStartup+40;
            SwimsuitClothRuntime cloth;
            while((cloth=FindAnyObjectByType<SwimsuitClothRuntime>())==null||!cloth.IsReady)
            {if(Time.realtimeSinceStartup>deadline){Application.Quit(1);yield break;}yield return null;}
            for(int i=0;i<30;i++)yield return null;
            bool pass=cloth.Solver.Particles.Length>100&&cloth.Solver.MaximumOffset>.001f;
            foreach(var particle in cloth.Solver.Particles)pass&=float.IsFinite(particle.position.sqrMagnitude);
            var skins=FindAnyObjectByType<SiSkinSwitcher>();
            pass&=skins.TrySelect("original");yield return null;
            pass&=skins.TrySelect("swimsuit");yield return null;yield return null;
            var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"-mgfr-cloth-output");
            string output=args[at+1];
            File.WriteAllText(output,$"particles={cloth.Solver.Particles.Length}\nconstraints={cloth.Solver.ConstraintCount}\noffsetMetres={cloth.Solver.MaximumOffset}\nlastCpuMilliseconds={cloth.LastMilliseconds}\nswitchAndFiniteCheck={pass}\n");
            Debug.Log("[Cloth quick check] pass="+pass);Application.Quit(pass?0:1);
        }
    }
}
