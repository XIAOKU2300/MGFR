using System.Collections;
using UnityEngine;
using MGFR.Character;

namespace MGFR.Experience
{
    // Retarget the two leg chains to this model's proportions. The VMD's toe
    // and ankle targets were authored on another rig and cannot both be reached.
    [DefaultExecutionOrder(900)]
    public sealed class LegPlantSolver : MonoBehaviour
    {
        Transform[] bones;
        public float AnkleError {get;private set;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()=>new GameObject("Idle leg planting").AddComponent<LegPlantSolver>();
        IEnumerator Start()
        {
            IdleMotionPlayer idle;
            while((idle=FindAnyObjectByType<IdleMotionPlayer>())==null)yield return null;
            bones=idle.GetComponent<SiCharacterLoader>().Renderer.bones;
        }
        void LateUpdate(){SolveNow();}
        public void SolveNow()
        {
            if(bones==null)return;
            AnkleError=0;
            Solve(21,22,23,24,7,8);Solve(25,26,27,28,10,11);
            bones[738].localRotation=bones[25].localRotation;
            bones[739].localRotation=bones[26].localRotation;
            bones[740].localRotation=bones[27].localRotation;
            bones[742].localRotation=bones[21].localRotation;
            bones[743].localRotation=bones[22].localRotation;
            bones[744].localRotation=bones[23].localRotation;
            var shoes=MGFR.Wardrobe.ShoeFootPose.Instance;
            if(shoes!=null&&shoes.Ready){bones[745].localRotation=bones[24].localRotation;bones[741].localRotation=bones[28].localRotation;}
        }
        void Solve(int h,int k,int a,int toe,int target,int toeTarget)
        {
            var hip=bones[h];var knee=bones[k];var ankle=bones[a];
            float scale=hip.lossyScale.x;
            Vector3 upper=knee.localPosition,lower=ankle.localPosition;
            var shoes=MGFR.Wardrobe.ShoeFootPose.Instance;
            bool shoePose=shoes!=null&&shoes.Ready;
            Vector3 lift=shoePose?shoes.transform.up*(shoes.Height*shoes.Weights[h==21?0:1]*scale):Vector3.zero;
            Vector3 goal=bones[target].position+lift-hip.position;
            float d=goal.magnitude/scale;
            float aa=Vector3.Dot(upper,lower),bb=Vector3.Dot(upper,Vector3.Cross(Vector3.right,lower));
            float cosine=Mathf.Clamp((d*d-upper.sqrMagnitude-lower.sqrMagnitude)/(2*Mathf.Sqrt(aa*aa+bb*bb)),-1,1);
            float angle=Mathf.Min(-.5f,(Mathf.Atan2(bb,aa)-Mathf.Acos(cosine))*Mathf.Rad2Deg);
            knee.localRotation=Quaternion.AngleAxis(angle,Vector3.right);
            Vector3 reach=hip.TransformVector(upper+knee.localRotation*lower);
            hip.rotation=Quaternion.FromToRotation(reach,goal)*hip.rotation;
            if(shoePose){ankle.rotation=bones[0].parent.rotation;bones[toe].localRotation=Quaternion.identity;}
            else ankle.rotation=Quaternion.FromToRotation(bones[toe].position-ankle.position,bones[toeTarget].position-ankle.position)*ankle.rotation;
            AnkleError=Mathf.Max(AnkleError,Vector3.Distance(ankle.position,bones[target].position+lift));
        }
    }
}
