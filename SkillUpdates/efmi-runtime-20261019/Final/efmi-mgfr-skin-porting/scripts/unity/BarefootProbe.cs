using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using MGFR.Character;

public static class BarefootProbe
{
    static string Arg(string name) { var a=Environment.GetCommandLineArgs();return a[Array.IndexOf(a,name)+1]; }
    static void WriteNew(string path, byte[] value) {using(var f=new FileStream(path,FileMode.CreateNew))f.Write(value,0,value.Length);}
    public static void Run()
    {
        try
        {
            string root=Arg("-skinRoot"),output=Arg("-probeDir");
            if(Directory.Exists(output))throw new Exception("Probe output already exists");Directory.CreateDirectory(output);
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            QualitySettings.skinWeights=SkinWeights.FourBones;QualitySettings.antiAliasing=4;
            RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.35f,.37f,.4f);
            var go=new GameObject("Independent swimsuit");var loader=go.AddComponent<SiCharacterLoader>();
            loader.buildOnStart=false;loader.dataRootOverride=root;loader.Build();
            if(!loader.IsReady)throw new Exception(loader.Status);
            var renderer=loader.Renderer;var mesh=renderer.sharedMesh;var bones=renderer.bones;
            var rotation=new Quaternion[bones.Length];for(int i=0;i<bones.Length;i++)rotation[i]=bones[i].localRotation;
            var original=mesh.vertices;var baked=new Mesh();renderer.BakeMesh(baked);float restError=0;
            var rest=baked.vertices;for(int i=0;i<rest.Length;i++)restError=Mathf.Max(restError,Vector3.Distance(original[i],rest[i]));
            if(restError>.0001f)throw new Exception("Rest bind error: "+restError);
            if(mesh.blendShapeCount!=40||bones.Length!=828)throw new Exception("Rig/morph contract mismatch");
            foreach(var m in renderer.sharedMaterials)if(m.shader==null||!m.shader.isSupported)throw new Exception("Unsupported shader");
            var key=new GameObject("Key").AddComponent<Light>();key.type=LightType.Directional;key.intensity=.7f;key.transform.rotation=Quaternion.Euler(35,-25,0);
            var fill=new GameObject("Fill").AddComponent<Light>();fill.type=LightType.Directional;fill.intensity=.25f;fill.transform.rotation=Quaternion.Euler(15,155,0);
            var floor=GameObject.CreatePrimitive(PrimitiveType.Plane);floor.name="Ground y=0";floor.transform.position=new Vector3(0,-.001f,0);floor.transform.localScale=Vector3.one*.35f;
            var floorMaterial=new Material(Shader.Find("Standard"));floorMaterial.color=new Color(.38f,.4f,.43f);floor.GetComponent<Renderer>().sharedMaterial=floorMaterial;
            var camera=new GameObject("Review camera").AddComponent<Camera>();camera.enabled=false;camera.clearFlags=CameraClearFlags.SolidColor;
            camera.backgroundColor=new Color(.20f,.23f,.27f);camera.orthographic=true;camera.orthographicSize=.98f;camera.nearClipPlane=.01f;camera.farClipPlane=20;
            var rt=new RenderTexture(1000,1300,24,RenderTextureFormat.ARGB32);rt.antiAliasing=4;camera.targetTexture=rt;
            var image=new Texture2D(1000,1300,TextureFormat.RGB24,false);
            var display=new GameObject("Baked validation geometry");var filter=display.AddComponent<MeshFilter>();var mr=display.AddComponent<MeshRenderer>();mr.sharedMaterials=renderer.sharedMaterials;
            Action<string,Vector3,Vector3> shot=(name,eye,target)=>{
                renderer.enabled=true;renderer.BakeMesh(baked);filter.sharedMesh=baked;renderer.enabled=false;
                camera.transform.position=eye;camera.transform.LookAt(target);camera.Render();RenderTexture.active=rt;
                image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();RenderTexture.active=null;
                WriteNew(Path.Combine(output,name+".png"),image.EncodeToPNG());
            };
            shot("01-front",new Vector3(0,.9f,-3),new Vector3(0,.9f,0));
            shot("02-back",new Vector3(0,.9f,3),new Vector3(0,.9f,0));
            shot("03-side",new Vector3(3,.9f,0),new Vector3(0,.9f,0));
            shot("04-threequarter",new Vector3(-2,.9f,-3),new Vector3(0,.9f,0));
            camera.orthographicSize=.16f;
            shot("09-feet-side",new Vector3(.8f,.105f,-.04f),new Vector3(.075f,.105f,-.04f));
            shot("10-feet-front",new Vector3(0,.10f,-1),new Vector3(0,.10f,-.04f));
            shot("11-feet-threequarter",new Vector3(.55f,.23f,-.65f),new Vector3(0,.09f,-.04f));
            camera.orthographicSize=.98f;
            bones[32].localRotation=Quaternion.Euler(0,0,45);bones[58].localRotation=Quaternion.Euler(0,0,-45);
            bones[35].localRotation=Quaternion.Euler(0,-45,0);bones[61].localRotation=Quaternion.Euler(0,45,0);
            shot("05-arms",new Vector3(0,.9f,-3),new Vector3(0,.9f,0));
            float maxArmDelta=0;var moved=baked.vertices;for(int i=0;i<moved.Length;i++)maxArmDelta=Mathf.Max(maxArmDelta,Vector3.Distance(rest[i],moved[i]));
            for(int i=0;i<bones.Length;i++)bones[i].localRotation=rotation[i];
            bones[21].localRotation=Quaternion.Euler(-25,0,-6);bones[22].localRotation=Quaternion.Euler(55,0,0);
            bones[742].localRotation=bones[21].localRotation;bones[743].localRotation=bones[22].localRotation;
            shot("06-leg",new Vector3(-2,.9f,-3),new Vector3(0,.9f,0));
            for(int i=0;i<bones.Length;i++)bones[i].localRotation=rotation[i];
            camera.orthographicSize=.24f;
            shot("07-face-neutral",new Vector3(0,1.5f,-2),new Vector3(0,1.5f,0));
            renderer.SetBlendShapeWeight(mesh.GetBlendShapeIndex("まばたき"),100);
            renderer.SetBlendShapeWeight(mesh.GetBlendShapeIndex("あ"),100);
            shot("08-blink-mouth",new Vector3(0,1.5f,-2),new Vector3(0,1.5f,0));
            renderer.enabled=true;renderer.BakeMesh(baked);float morphDelta=0;var shape=baked.vertices;
            for(int i=0;i<shape.Length;i++)morphDelta=Mathf.Max(morphDelta,Vector3.Distance(rest[i],shape[i]));
            if(maxArmDelta<.1f||morphDelta<.001f)throw new Exception("Pose/morph did not move geometry");
            var report="Unity="+Application.unityVersion+"\nvertices="+mesh.vertexCount+"\ntriangles="+mesh.triangles.Length/3+"\nmaterials="+mr.sharedMaterials.Length+
                "\nbones="+bones.Length+"\nblendShapes="+mesh.blendShapeCount+"\nmaxRestBindErrorMetres="+restError+"\nmaxArmDeltaMetres="+maxArmDelta+
                "\nmaxBlinkMouthDeltaMetres="+morphDelta+"\nmode=isolated editor render; no headset or live project test\n";
            WriteNew(Path.Combine(output,"unity-checks.txt"),System.Text.Encoding.UTF8.GetBytes(report));Debug.Log(report);
            EditorApplication.Exit(0);
        }
        catch(Exception e){Debug.LogException(e);EditorApplication.Exit(1);}
    }
}
