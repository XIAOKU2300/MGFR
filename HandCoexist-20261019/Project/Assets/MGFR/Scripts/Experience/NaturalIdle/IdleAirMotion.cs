using System.Collections;
using UnityEngine;
using MGFR.PhysicsRig;

namespace MGFR.Experience
{
    public sealed class IdleAirMotion : MonoBehaviour
    {
        PmxSecondaryPhysics physics;
        IdleMotionPlayer idle;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()=>new GameObject("Natural idle secondary air").AddComponent<IdleAirMotion>();
        IEnumerator Start()
        {
            while((physics=FindAnyObjectByType<PmxSecondaryPhysics>())==null||!physics.IsReady||
                  (idle=FindAnyObjectByType<IdleMotionPlayer>())==null)yield return null;
            physics.BeforeSubstep+=ApplyAir;
        }
        void ApplyAir(float delta,float progress)
        {
            if(!idle.NaturalIdle)return;
            for(int i=0;i<physics.Bodies.Length;i++)
            {
                var rb=physics.Bodies[i];int group=physics.Data.bodies[i].group;
                if(rb.isKinematic||group<4)continue;
                // Preserve original material damping, joints, colliders and grabs.
                float material=group==4?1.0f:group==7||group==10?1.1f:group==9?.55f:.70f;
                rb.AddForce(idle.Natural.Air(idle.MotionSeconds,(i%7)/7f)*material,ForceMode.Acceleration);
            }
        }
        void OnDestroy(){if(physics!=null)physics.BeforeSubstep-=ApplyAir;}
    }
}
