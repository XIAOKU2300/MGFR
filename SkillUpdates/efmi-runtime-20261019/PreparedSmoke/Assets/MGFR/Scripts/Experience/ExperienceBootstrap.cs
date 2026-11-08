using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;
using MGFR.Character;
using MGFR.Attention;

namespace MGFR.Experience
{
    public sealed class ExperienceBootstrap : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if (SceneManager.GetActiveScene().name == SiCharacterBootstrap.SceneName)
                new GameObject("MGFR Experience").AddComponent<ExperienceBootstrap>();
        }

        IEnumerator Start()
        {
            SiCharacterLoader loader;
            while ((loader = FindAnyObjectByType<SiCharacterLoader>()) == null || !loader.IsReady)
                yield return null;
            CalibrateRest(loader);
            var bones = loader.Renderer.bones;
            var attention = loader.gameObject.AddComponent<FaceAttentionController>();
            attention.RequireTrackedHeadset = !MGFR.SmokeTest.XrDeviceFollower.Suppressed;
            attention.ViewerTarget = Camera.main.transform;
            attention.BlushWriter = value => loader.BlushWeight = value;
            attention.Bind(loader.transform, loader.Renderer, bones[16], bones[17], bones[19], bones[20]);
            var idle = loader.gameObject.AddComponent<IdleMotionPlayer>();
            idle.Bind(loader, attention);
            var hands = gameObject.AddComponent<ControllerHands>();
            hands.Bind(loader);
            var skirt = loader.gameObject.AddComponent<SkirtDynamics>();
            skirt.Bind(loader, hands);
            Debug.Log("[MGFR experience] idle + controller hands + skirt physics + attention ready");
            if (System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-mgfr-experience-check") >= 0)
                gameObject.AddComponent<ExperienceCheck>().Bind(loader, idle, hands, skirt, attention);
        }

        // Correct the known legacy export once, before any animation writes bones.
        // Model files and the original PMX remain untouched.
        static void CalibrateRest(SiCharacterLoader loader)
        {
            var data = loader.Data.bones;
            if (data[17].positionScaled[1] < 3f) return;
            var absolute = new Vector3[data.Length];
            for (int i=0;i<data.Length;i++)
            {
                var p=data[i].localScaled;
                absolute[i]=new Vector3(p[0],p[1],p[2]);
            }
            var bind = new Matrix4x4[data.Length];
            for (int i=0;i<data.Length;i++)
            {
                var local=absolute[i]-(data[i].parent>=0?absolute[data[i].parent]:Vector3.zero);
                loader.Renderer.bones[i].localPosition=local;
                data[i].localScaled=new[]{local.x,local.y,local.z};
                var a=absolute[i]; data[i].positionScaled=new[]{a.x,a.y,a.z};
                bind[i]=Matrix4x4.Translate(-a);
            }
            var mesh=Instantiate(loader.Renderer.sharedMesh);
            mesh.name="Si calibrated runtime mesh";
            mesh.bindposes=bind;loader.Renderer.sharedMesh=mesh;
            loader.Renderer.updateWhenOffscreen=true;
            Debug.Log("[MGFR experience] repaired legacy rest/bind coordinates for 828 bones");
        }
    }
}
