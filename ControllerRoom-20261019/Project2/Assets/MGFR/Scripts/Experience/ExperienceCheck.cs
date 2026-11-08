using System.Collections;
using System.IO;
using UnityEngine;
using MGFR.Character;
using MGFR.Attention;

namespace MGFR.Experience
{
    // Runs only with the explicit -mgfr-experience-check flag.
    public sealed class ExperienceCheck : MonoBehaviour
    {
        SiCharacterLoader loader;IdleMotionPlayer idle;ControllerHands hands;
        SkirtDynamics skirt;FaceAttentionController face;
        string folder;
        int failures;
        public void Bind(SiCharacterLoader l,IdleMotionPlayer i,ControllerHands h,SkirtDynamics s,FaceAttentionController f)
        {loader=l;idle=i;hands=h;skirt=s;face=f;}
        void Check(bool value,string name)
        {
            Debug.Log("[EXPERIENCE CHECK] "+(value?"PASS ":"FAIL ")+name);
            if(!value)failures++;
        }
        IEnumerator Start()
        {
            string[] args=System.Environment.GetCommandLineArgs();
            int index=System.Array.IndexOf(args,"-mgfr-check-dir");
            folder=args[index+1];Directory.CreateDirectory(folder);
            yield return new WaitForSeconds(.5f);
            var rig=loader.Renderer.bones;Vector3 worldAnchor=loader.transform.position;
            var initial=rig[64].position;
            float travel=0,peak=0,cpu=0,foot=0;Vector3 footStart=rig[23].position;
            float start=Time.time;
            for(int shot=0;shot<5;shot++)
            {
                float until=start+shot*1.12f;
                while(Time.time<until)
                {
                    travel=Mathf.Max(travel,Vector3.Distance(initial,rig[64].position));
                    foot=Mathf.Max(foot,Vector3.Distance(footStart,rig[23].position));
                    peak=Mathf.Max(peak,skirt.PeakDisplacement);cpu=Mathf.Max(cpu,skirt.LastMilliseconds);
                    yield return null;
                }
                yield return new WaitForEndOfFrame();
                ScreenCapture.CaptureScreenshot(Path.Combine(folder,"idle-"+shot+".png"));
            }
            Check(idle.BoundBones>=80,"idle rig loaded");
            Check(travel>.002f,"actual wrist moves across idle cycle");
            Check(Vector3.Distance(worldAnchor,loader.transform.position)<.00001f,"room anchor stays fixed");
            Check(rig[17].position.y<2.2f,"calibrated skeleton head position");
            Check(face.LeftIrisVertices>20&&face.RightIrisVertices>20,"both actual eyes calibrated");
            Check(peak>.0001f&&peak<.12f,"skirt moves within a small envelope");
            hands.TestInput=true;
            hands.SetSimulatedHand(0,hands.Ball.position,true);hands.UpdateGrab();
            Check(hands.BallOwner==0,"proxy hand grabs rigid ball");
            Vector3 goal=hands.Hands[0].Position+new Vector3(.2f,.15f,0);
            hands.SetSimulatedHand(0,goal,true);hands.UpdateGrab();
            Check(Vector3.Distance(hands.Ball.position,goal)<.001f,"grab follows hand");
            hands.SetSimulatedHand(0,goal+new Vector3(.01f,0,0),false);hands.UpdateGrab();
            Check(hands.BallOwner==-1&&!hands.Ball.isKinematic,"release restores rigid body simulation");
            hands.SetSimulatedHand(0,rig[644].position+new Vector3(0,0,.02f),false);
            yield return new WaitForSeconds(.25f);
            Check(skirt.HandContacts>0,"hand pushes skirt solver");
            yield return new WaitForEndOfFrame();
            ScreenCapture.CaptureScreenshot(Path.Combine(folder,"contact.png"));
            hands.SetSimulatedHand(0,Vector3.zero,false,false);
            yield return new WaitForSeconds(1);
            Check(skirt.PeakDisplacement<.12f,"skirt settles after hand release");
            float maxError=0;
            foreach(var v in loader.Renderer.bones)
                if(float.IsNaN(v.position.sqrMagnitude)||float.IsInfinity(v.position.sqrMagnitude))maxError++;
            Check(maxError==0,"all 828 bone positions finite");
            string report=$"failures={failures}\nidleWristTravelM={travel}\nleftFootTravelM={foot}\nskirtPeakM={peak}\nskirtPeakCpuMs={cpu}\n";
            File.WriteAllText(Path.Combine(folder,"result.txt"),report);
            Debug.Log("[EXPERIENCE CHECK] "+report.Replace('\n',' '));
            yield return new WaitForSeconds(.5f);
            Application.Quit(failures==0?0:1);
        }
    }
}
