using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using MGFR.Character;
using MGFR.Experience;
using MGFR.Attention;
using MGFR.BareHands;
using MGFR.Skins;

public sealed class SkinSwitchReview : MonoBehaviour
{
    readonly List<string> report = new List<string> { "source=ACTUAL_UNITY_DESKTOP_RENDER_AND_SYNTHETIC_HANDS_NOT_HEADSET" };
    string output;
    bool finished;
    SiSkinSwitcher skins;
    BareHandInteraction hands;
    SiCharacterLoader loader;
    Mesh bake;
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Install()
    {
        if (Array.IndexOf(Environment.GetCommandLineArgs(), "-mgfr-skin-review") >= 0)
            new GameObject("Skin integration review").AddComponent<SkinSwitchReview>();
    }
    void Check(string label, bool value)
    {
        report.Add(label + "=" + value);
        if (!value) throw new InvalidOperationException(label + " failed");
    }
    IEnumerator Start()
    {
        var args = Environment.GetCommandLineArgs(); int at = Array.IndexOf(args, "-mgfr-skin-output");
        output = args[at + 1]; Directory.CreateDirectory(output);
        Application.logMessageReceived += LogFailure;
        float deadline = Time.realtimeSinceStartup + 60;
        while ((skins = FindAnyObjectByType<SiSkinSwitcher>()) == null || !skins.IsReady)
        {
            if (Time.realtimeSinceStartup > deadline) { Finish(false, "initialization timeout"); yield break; }
            yield return null;
        }
        loader = skins.Loader; hands = FindAnyObjectByType<BareHandInteraction>();
        Check("startupSwimsuit", skins.CurrentId == "swimsuit");
        var bones = loader.Renderer.bones; var bodies = hands.Physics.Bodies;
        var character = loader.GetComponent<SiCharacterController>();
        var idle = loader.GetComponent<IdleMotionPlayer>();
        var attention = loader.GetComponent<FaceAttentionController>();
        var legs = FindAnyObjectByType<LegPlantSolver>();
        character.enabled = false; idle.enabled = false; attention.AutoUpdate = false;
        legs.enabled = false; hands.enabled = false; hands.Physics.enabled = false;
        hands.Source.Replay = true;
        FindAnyObjectByType<ControllerHands>().Ball.position = Vector3.one * 10;
        var placement = loader.transform.position; var rotation = loader.transform.rotation;
        var scale = loader.transform.localScale;
        bake = new Mesh();
        int originalTriangles = 0, swimTriangles = 0;
        foreach (string id in new[] { "original", "swimsuit", "original", "swimsuit", "original", "swimsuit" })
        {
            Check("select_" + id, skins.TrySelect(id));
            Check("boneIdentity_" + id, loader.Renderer.bones[17] == bones[17] && loader.Renderer.bones[27] == bones[27]);
            Check("physicsIdentity_" + id, hands.Physics.Bodies[0] == bodies[0]);
            Check("placement_" + id, loader.transform.position == placement && loader.transform.rotation == rotation && loader.transform.localScale == scale);
            SetRest();
            loader.Renderer.BakeMesh(bake);
            var posed = bake.vertices; var rest = loader.Renderer.sharedMesh.vertices;
            float max = 0; for (int i = 0; i < rest.Length; i++) max = Mathf.Max(max, Vector3.Distance(rest[i], posed[i]));
            report.Add("restBakeErrorMetres_" + id + "=" + max.ToString("G9"));
            Check("bindMatchesRest_" + id, max < .0001f);
            Check("morphs_" + id, loader.Renderer.sharedMesh.blendShapeCount == 40);
            if (id == "original") originalTriangles = hands.SkinSurfaceTriangles; else swimTriangles = hands.SkinSurfaceTriangles;
        }
        report.Add("originalSurfaceTriangles=" + originalTriangles + "; swimsuitSurfaceTriangles=" + swimTriangles);
        Check("surfaceTopologyRebuilt", originalTriangles > 0 && swimTriangles > 0 && originalTriangles != swimTriangles);
        int blink = loader.Renderer.sharedMesh.GetBlendShapeIndex("まばたき");
        loader.Renderer.SetBlendShapeWeight(blink, 65);
        Check("selectWithMorph", skins.TrySelect("original") && skins.TrySelect("swimsuit"));
        Check("expressionPreserved", Mathf.Abs(loader.Renderer.GetBlendShapeWeight(blink) - 65) < .01f);
        SetRest(); loader.Renderer.BakeMesh(bake); var neutral = bake.vertices;
        loader.Renderer.SetBlendShapeWeight(blink, 100); loader.Renderer.BakeMesh(bake); var changed = bake.vertices;
        float morphDelta = 0; for (int i = 0; i < changed.Length; i++) morphDelta = Mathf.Max(morphDelta, Vector3.Distance(changed[i], neutral[i]));
        Check("blinkMovesGeometry", morphDelta > .001f);
        report.Add("blinkMaxDelta=" + morphDelta);
        SetRest();
        for (int step = 0; step < 70; step++) idle.Apply(.9f, 1f / 72);
        loader.Renderer.BakeMesh(bake); changed = bake.vertices;
        float motion = 0; for (int i = 0; i < changed.Length; i++) motion = Mathf.Max(motion, Vector3.Distance(changed[i], neutral[i]));
        Check("idleMovesGeometry", motion > .01f); report.Add("idleMaxDelta=" + motion);

        // Exercise a real skinned surface in the new topology and the actual
        // manual hand/PhysX path. No phantom old skirt/sleeve collider is accepted.
        SetRest(); hands.Physics.ResetToAnimation();
        using (var query = new HandSurfaceQuery(hands.Physics))
        {
            loader.Renderer.BakeMesh(bake); var vertices = bake.vertices;
            Vector3 contact = Vector3.zero; int body = -1;
            for (int i = 0; i < vertices.Length; i += 3)
            {
                var world = loader.transform.TransformPoint(vertices[i]);
                if (query.Find(world, .003f, -1, out int found, out var model) && hands.Physics.Data.bodies[found].group == 8)
                { contact = loader.transform.TransformPoint(model); body = found; break; }
            }
            Check("swimsuitRibbonSurfaceFound", body >= 0);
            for (int step = 0; step < 18; step++)
            {
                hands.Source.SetReplayFrame(0, PoseAt(contact, false), true);
                hands.StepInteraction(1f / 72); hands.Physics.Tick(1f / 72);
            }
            for (int step = 0; step < 12; step++)
            {
                hands.Source.SetReplayFrame(0, PoseAt(contact, true), true);
                hands.StepInteraction(1f / 72); hands.Physics.Tick(1f / 72);
            }
            Check("pinchAcquiresAfterSkinChange", hands.GrabbedBody[0] >= 0);
            int grabbed = hands.GrabbedBody[0];
            var before = hands.Physics.Bodies[grabbed].position;
            for (int step = 0; step < 54; step++)
            {
                var target = contact - loader.transform.forward * (.04f * (step + 1) / 54);
                hands.Source.SetReplayFrame(0, PoseAt(target, true), true);
                hands.StepInteraction(1f / 72); hands.Physics.Tick(1f / 72);
            }
            float drag = Vector3.Distance(before, hands.Physics.Bodies[grabbed].position) * Mathf.Abs(loader.transform.lossyScale.x);
            report.Add("ribbonDragWorldMetres=" + drag);
            Check("ribbonDragMovesBody", drag > .005f);
            Check("switchWhileGrabbing", skins.TrySelect("original"));
            Check("grabReleasedOnSwitch", hands.GrabbedBody[0] < 0);
            Check("returnToSwimsuit", skins.TrySelect("swimsuit"));
            hands.Source.SetReplayFrame(0, PoseAt(contact, false), false);
        }
        SetRest();
        var basePose = new Vector3[bones.Length];
        for (int i = 0; i < bones.Length; i++) basePose[i] = bones[i].localPosition;
        for (int step = 0; step < 70; step++) idle.Apply(.9f, 1f / 72);
        // Render the prepared animation pose, not a generated illustration.
        var camera = new GameObject("Skin review camera").AddComponent<Camera>();
        camera.CopyFrom(Camera.main); camera.enabled = false;
        loader.gameObject.layer = 8; camera.cullingMask = 1 << 8;
        camera.stereoTargetEye = StereoTargetEyeMask.None;
        camera.clearFlags = CameraClearFlags.SolidColor; camera.backgroundColor = new Color(.09f, .105f, .12f);
        camera.allowHDR = false;
        var targetTexture = new RenderTexture(1100, 1600, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
        targetTexture.Create(); camera.targetTexture = targetTexture; camera.aspect = 1100f / 1600;
        var image = new Texture2D(1100, 1600, TextureFormat.RGB24, false);
        var views = new[] {
            new Vector3(0,.9f,-2.65f), new Vector3(.60f,1.48f,-.86f),
            new Vector3(.65f,.9f,2.55f), new Vector3(.8f,.095f,-.12f), new Vector3(.26f,.14f,-.5f)
        };
        var aim = new[] {new Vector3(0,.87f,0),new Vector3(0,1.47f,0),new Vector3(0,.87f,0),new Vector3(0,.11f,-.01f),new Vector3(0,.11f,0)};
        string[] names = {"01-fullbody", "02-face", "03-back", "04-feet-side", "05-feet-front"};
        float[] fovs = {43,34,43,36,42}; int magenta = 0;
        for (int i = 0; i < views.Length; i++)
        {
            camera.transform.position = loader.transform.TransformPoint(views[i]);
            camera.transform.LookAt(loader.transform.TransformPoint(aim[i])); camera.fieldOfView = fovs[i];
            skins.Style.SetActive(true); Save(camera, image, names[i] + "-zmd.png");
            foreach(var pixel in image.GetPixels32()) if(pixel.r>230&&pixel.g<25&&pixel.b>230)magenta++;
            if(i==0){skins.Style.SetActive(false);Save(camera,image,names[i]+"-current-style.png");skins.Style.SetActive(true);}
            yield return null;
        }
        Check("noErrorMagentaPixels", magenta == 0);
        var material = loader.Materials[8];
        Check("swimsuitNormalBinding", material.GetTexture("_NormalMap").name.Contains("swimsuit_cloth_N"));
        Check("swimsuitEmissionCleared", material.GetFloat("_EmissionIntensity") == 0);
        Check("transparentDepthPreserved", loader.Materials[10].GetFloat("_ZWrite") == skins.CurrentAppearance.Materials[10].GetFloat("_ZWrite"));
        camera.backgroundColor=Color.green;Save(camera,image,"06-mr-green.png");
        var corner=image.GetPixel(0,0);Check("pureGreenBackground",corner.g>.99f&&corner.r<.005f&&corner.b<.005f);
        Check("originalSkinRestored", skins.TrySelect("original"));
        camera.backgroundColor=new Color(.09f,.105f,.12f); camera.transform.position=loader.transform.TransformPoint(views[0]);
        camera.transform.LookAt(loader.transform.TransformPoint(aim[0]));camera.fieldOfView=fovs[0];
        Save(camera,image,"07-original-restored.png");
        Check("swimsuitLoadedFinally",skins.TrySelect("swimsuit"));
        report.Add("switchCount="+skins.SwitchCount);
        camera.targetTexture=null;targetTexture.Release();Destroy(image);Destroy(targetTexture);Destroy(bake);
        Finish(true, "");
    }
    void SetRest()
    {
        var bones=loader.Renderer.bones;
        for(int i=0;i<bones.Length;i++){var p=loader.Data.bones[i].localScaled;bones[i].localPosition=new Vector3(p[0],p[1],p[2]);bones[i].localRotation=Quaternion.identity;}
        for(int i=0;i<loader.Renderer.sharedMesh.blendShapeCount;i++)loader.Renderer.SetBlendShapeWeight(i,0);
    }
    void Save(Camera camera,Texture2D image,string name)
    {
        camera.Render();RenderTexture.active=camera.targetTexture;
        image.ReadPixels(new Rect(0,0,image.width,image.height),0,0);image.Apply();RenderTexture.active=null;
        File.WriteAllBytes(Path.Combine(output,name),image.EncodeToPNG());
    }
    static Pose[] PoseAt(Vector3 point,bool pinch)
    {
        var p=new Pose[26];p[0]=new Pose(Vector3.zero,Quaternion.identity);p[1]=new Pose(Vector3.down*.05f,Quaternion.identity);
        p[2]=new Pose(new Vector3(-.035f,-.025f,0),Quaternion.identity);
        for(int i=3;i<6;i++)p[i]=new Pose(p[i-1].position+new Vector3(-.015f,.025f,0),Quaternion.identity);
        for(int finger=0;finger<4;finger++)for(int j=0;j<5;j++)p[6+finger*5+j]=new Pose(new Vector3(-.03f+finger*.02f,.012f+j*.023f,0),Quaternion.identity);
        if(pinch)p[5].position=p[10].position+Vector3.left*.018f;
        var center=(p[5].position+p[10].position)*.5f;
        for(int i=0;i<26;i++)p[i].position+=point-center;return p;
    }
    void LogFailure(string message,string trace,LogType type)
    {if(type==LogType.Exception||type==LogType.Error)Finish(false,message);}
    void Finish(bool pass,string error)
    {
        if(finished)return;finished=true;Application.logMessageReceived-=LogFailure;
        if(error.Length>0)report.Add("error="+error);report.Add("pass="+pass);
        File.WriteAllLines(Path.Combine(output,"skin-checks.txt"),report);Debug.Log("[Skin review] "+string.Join(" ",report));
        #if UNITY_EDITOR
        UnityEditor.EditorApplication.Exit(pass?0:1);
        #else
        Application.Quit(pass?0:1);
        #endif
    }
}
