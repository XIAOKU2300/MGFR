using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Character;

namespace MGFR.Experience
{
    public sealed class ExperienceVisualCheck : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Install()
        {
            if(System.Array.IndexOf(System.Environment.GetCommandLineArgs(),"-mgfr-visual-check")>=0)
                new GameObject("Experience render check").AddComponent<ExperienceVisualCheck>();
        }
        IEnumerator Start()
        {
            var args=System.Environment.GetCommandLineArgs();
            string folder=args[System.Array.IndexOf(args,"-mgfr-check-dir")+1];
            Directory.CreateDirectory(folder);
            IdleMotionPlayer idle;
            while((idle=FindAnyObjectByType<IdleMotionPlayer>())==null)yield return null;
            yield return new WaitForSeconds(.3f);
            var loader=idle.GetComponent<SiCharacterLoader>();var rig=loader.Renderer.bones;
            var legs=FindAnyObjectByType<LegPlantSolver>();var skirt=FindAnyObjectByType<SkirtDynamics>();
            var camera=new GameObject("Render proof camera").AddComponent<Camera>();
            camera.CopyFrom(Camera.main);camera.stereoTargetEye=StereoTargetEyeMask.None;camera.enabled=false;
            camera.transform.position=loader.transform.TransformPoint(new Vector3(0,1f,-2.4f));
            camera.transform.LookAt(loader.transform.TransformPoint(Vector3.up*.9f));
            var rt=new RenderTexture(900,900,24,RenderTextureFormat.ARGB32);camera.targetTexture=rt;
            var image=new Texture2D(900,900,TextureFormat.RGB24,false);
            float ankleError=0,peak=0,cost=0;Vector3 anchor=loader.transform.position;
            float started=Time.time;
            for(int i=0;i<24;i++)
            {
                while(Time.time<started+i*idle.Duration/24f)yield return null;
                ankleError=Mathf.Max(ankleError,legs.AnkleError);peak=Mathf.Max(peak,skirt.PeakDisplacement);cost=Mathf.Max(cost,skirt.LastMilliseconds);
                camera.Render();RenderTexture.active=rt;
                image.ReadPixels(new Rect(0,0,900,900),0,0);image.Apply();RenderTexture.active=null;
                File.WriteAllBytes(Path.Combine(folder,$"pose-{i:00}.png"),image.EncodeToPNG());
            }
            var hands=FindAnyObjectByType<ControllerHands>();hands.TestInput=true;
            hands.SetSimulatedHand(0,rig[644].position+new Vector3(0,0,.015f),false);
            yield return new WaitForSeconds(.3f);
            camera.Render();RenderTexture.active=rt;
            image.ReadPixels(new Rect(0,0,900,900),0,0);image.Apply();RenderTexture.active=null;
            File.WriteAllBytes(Path.Combine(folder,"skirt-contact.png"),image.EncodeToPNG());
            bool pass=ankleError<.002f&&Vector3.Distance(anchor,loader.transform.position)<.00001f;
            string report=$"pass={pass}\nmaxAnkleErrorM={ankleError}\nskirtPeakM={peak}\nskirtPeakCpuMs={cost}\n";
            File.WriteAllText(Path.Combine(folder,"visual-result.txt"),report);
            Debug.Log("[EXPERIENCE VISUAL] "+report.Replace('\n',' '));
            camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(image);
            yield return new WaitForSeconds(.2f);Application.Quit(pass?0:1);
        }
    }
}
