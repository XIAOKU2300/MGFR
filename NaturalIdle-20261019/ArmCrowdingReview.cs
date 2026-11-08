using System;
using UnityEngine;
using MGFR.Character;

namespace MGFR.Experience
{
    // Explicit replay only. Gently close the arms another five degrees, hold,
    // then release. This reproduces the garment/arm pinch without real tracking.
    [DefaultExecutionOrder(850)]
    public sealed class ArmCrowdingReview : MonoBehaviour
    {
        IdleMotionPlayer idle;SiCharacterLoader loader;float start=-1;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"-mgfr-natural-idle-review")>=0)
                new GameObject("Arm garment crowding replay").AddComponent<ArmCrowdingReview>();
        }
        void LateUpdate()
        {
            if(idle==null){idle=FindAnyObjectByType<IdleMotionPlayer>();return;}
            if(loader==null){loader=idle.GetComponent<SiCharacterLoader>();start=Time.unscaledTime;}
            float t=Time.unscaledTime-start;
            float weight=Mathf.SmoothStep(0,1,Mathf.Clamp01((t-5)/1.5f))*
                (1-Mathf.SmoothStep(0,1,Mathf.Clamp01((t-8)/1.5f)));
            if(weight<=0)return;
            var bones=loader.Renderer.bones;
            bones[32].rotation=Quaternion.AngleAxis(-5*weight,loader.transform.forward)*bones[32].rotation;
            bones[58].rotation=Quaternion.AngleAxis(5*weight,loader.transform.forward)*bones[58].rotation;
        }
    }
}
