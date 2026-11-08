using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using MGFR.Character;
using MGFR.Wardrobe;

public static class WardrobeProbe
{
    sealed class GeometryOnlyFootPermit : IWardrobeFootPoseOwner
    {
        public bool CanChangeShoe(string id,bool equipped)=>true;
        public void ShoeStateChanged(string id,bool equipped){}
    }
    static string Arg(string name){var a=Environment.GetCommandLineArgs();return a[Array.IndexOf(a,name)+1];}
    static void Check(bool value,string label){if(!value)throw new Exception(label);}
    static void NewFile(string path,byte[] bytes){using(var f=new FileStream(path,FileMode.CreateNew))f.Write(bytes,0,bytes.Length);}
    public static void Run()
    {
        try
        {
            string package=Arg("-wardrobePackage"),output=Arg("-wardrobeReview");
            if(Directory.Exists(output))throw new Exception("Review output already exists");Directory.CreateDirectory(output);
            var results=new List<string>{"mode=ISOLATED_UNITY_EDITOR_NOT_HAND_TRACKING_NOT_VR", "footPermit=GEOMETRY_ONLY_NO_FLAT_FOOT_CLAIM"};
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            RenderSettings.ambientMode=AmbientMode.Flat;RenderSettings.ambientLight=new Color(.4f,.42f,.45f);
            var light=new GameObject("Key").AddComponent<Light>();light.type=LightType.Directional;light.intensity=.8f;light.transform.rotation=Quaternion.Euler(25,-30,0);
            var camera=new GameObject("Review camera").AddComponent<Camera>();camera.enabled=false;camera.orthographic=true;
            camera.orthographicSize=1.03f;camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.16f,.18f,.21f);
            camera.nearClipPlane=.01f;camera.farClipPlane=20;
            var rt=new RenderTexture(1100,1400,24,RenderTextureFormat.ARGB32){antiAliasing=4};rt.Create();camera.targetTexture=rt;
            var image=new Texture2D(1100,1400,TextureFormat.RGB24,false);
            Action<string,Vector3,Vector3> shot=(name,eye,aim)=>{
                camera.transform.position=eye;camera.transform.LookAt(aim);camera.Render();
                var previous=RenderTexture.active;RenderTexture.active=rt;image.ReadPixels(new Rect(0,0,1100,1400),0,0);image.Apply();RenderTexture.active=previous;
                NewFile(Path.Combine(output,name+".png"),image.EncodeToPNG());
            };
            foreach(string id in new[]{"barefoot_v4","shod_v3"})
            {
                string root=Path.Combine(package,id);
                var go=new GameObject(id);var loader=go.AddComponent<SiCharacterLoader>();loader.buildOnStart=false;
                loader.dataRootOverride=Path.Combine(root,"model");loader.logMaterialTable=false;loader.Build();Check(loader.IsReady,loader.Status);
                var renderer=loader.Renderer;var source=renderer.sharedMesh;int[] full=source.triangles;
                var baked=new Mesh();renderer.BakeMesh(baked);float bindError=0;var verts=source.vertices;var b=baked.vertices;
                for(int i=0;i<verts.Length;i++)bindError=Mathf.Max(bindError,Vector3.Distance(verts[i],b[i]));
                Check(bindError<.0001f,"Rest bind error");
                var adapter=new WardrobeAdapter(renderer,root);
                shot(id+"-01-equipped",new Vector3(0,.92f,-3),new Vector3(0,.92f,0));
                int tested=0;
                foreach(var part in adapter.Profile.parts)
                {
                    var anchor=adapter.AnchorWorld(part.id);Check(Vector3.Distance(anchor,renderer.transform.TransformPoint(b[part.anchors[0].vertex]))<.0001f,"Anchor does not match skinned vertex");
                    if(part.requiresClothOwnershipHandoff)
                    {
                        adapter.SimulatedClothActive=true;
                        Check(!adapter.TryDetach(part.id,out _,out _),"Cloth handoff must be required");
                        Check(renderer.sharedMesh.triangles.Length==full.Length,"Rejected cloth request changed geometry");
                        adapter.SimulatedClothActive=false;
                    }
                    if(part.requiresFootPoseTransition)
                    {
                        adapter.FootPoseOwner=null;
                        Check(!adapter.TryDetach(part.id,out _,out _),"Foot-pose handoff must be required");
                        adapter.FootPoseOwner=new GeometryOnlyFootPermit();
                    }
                    Check(adapter.TryDetach(part.id,out var piece,out var reason),reason);
                    Check(renderer.sharedMesh.triangles.Length==full.Length-part.indexCount,"Wrong garment hidden");
                    Check(piece.GetComponent<MeshFilter>().sharedMesh.triangles.Length==part.indexCount,"Detached geometry incomplete");
                    Check(!adapter.TryDetach(part.id,out _,out _),"Duplicate detach allowed");
                    piece.transform.localPosition=new Vector3(.58f,0,0);
                    if(part.id=="cover_skirt"||part.id=="sleeve_left")shot(id+"-02-detached-"+part.id,new Vector3(.15f,.92f,-3),new Vector3(.15f,.92f,0));
                    if(part.id.StartsWith("shoe"))
                    {
                        camera.orthographicSize=.34f;
                        shot(id+"-shoe-"+part.id,new Vector3(.1f,.18f,-2),new Vector3(.1f,.18f,0));camera.orthographicSize=1.03f;
                    }
                    Check(adapter.TryEquip(part.id,out reason),reason);
                    Check(renderer.sharedMesh.triangles.SequenceEqual(full),"Equip did not restore exact triangles/order");
                    tested++;
                }
                adapter.FootPoseOwner=new GeometryOnlyFootPermit();
                foreach(var part in adapter.Profile.parts)Check(adapter.TryDetach(part.id,out _,out _),"Combination detach failed");
                foreach(var t in go.GetComponentsInChildren<MeshRenderer>())t.enabled=false;
                shot(id+"-03-all-accessories-off",new Vector3(0,.92f,-3),new Vector3(0,.92f,0));
                foreach(var part in adapter.Profile.parts.Reverse())Check(adapter.TryEquip(part.id,out _),"Reverse-order equip failed");
                Check(renderer.sharedMesh.triangles.SequenceEqual(full),"Combination restore mismatch");
                shot(id+"-04-restored",new Vector3(0,.92f,-3),new Vector3(0,.92f,0));
                loader.Renderer.bones[32].localRotation=Quaternion.Euler(0,0,32);
                renderer.BakeMesh(baked);var posed=baked.vertices;
                var sleeve=adapter.GetPart("sleeve_left");
                Check(Vector3.Distance(adapter.AnchorWorld("sleeve_left"),renderer.transform.TransformPoint(posed[sleeve.anchors[0].vertex]))<.0001f,"Anchor does not follow animated bone");
                shot(id+"-05-raised-arm",new Vector3(0,.92f,-3),new Vector3(0,.92f,0));
                int blink=source.GetBlendShapeIndex("まばたき"),mouth=source.GetBlendShapeIndex("あ");
                Check(blink>=0&&mouth>=0,"Missing face morph contract");renderer.SetBlendShapeWeight(blink,100);renderer.SetBlendShapeWeight(mouth,100);
                renderer.BakeMesh(baked);float morphDelta=0;var changed=baked.vertices;
                for(int i=0;i<changed.Length;i++)morphDelta=Mathf.Max(morphDelta,Vector3.Distance(changed[i],posed[i]));
                Check(morphDelta>.001f,"Face morph no longer moves geometry");
                bool wrongRejected=false;try{using(var wrong=new WardrobeAdapter(renderer,Path.Combine(package,id=="shod_v3"?"barefoot_v4":"shod_v3"))){} }catch(InvalidDataException){wrongRejected=true;}
                Check(wrongRejected,"Wrong profile accepted");
                adapter.Dispose();Check(renderer.sharedMesh==source,"Dispose did not return original mesh");
                results.Add(id+": partsTested="+tested+" exactRoundTrip=true combinationRoundTrip=true anchorsFollowBones=true clothGuard=true footGuard=true wrongProfileRejected=true bindError="+bindError+" morphDelta="+morphDelta);
                UnityEngine.Object.DestroyImmediate(go);UnityEngine.Object.DestroyImmediate(baked);
            }
            results.Add("pass=true");NewFile(Path.Combine(output,"unity-checks.txt"),System.Text.Encoding.UTF8.GetBytes(string.Join("\n",results)));
            Debug.Log(string.Join("\n",results));EditorApplication.Exit(0);
        }
        catch(Exception e){Debug.LogException(e);EditorApplication.Exit(1);}
    }
}
