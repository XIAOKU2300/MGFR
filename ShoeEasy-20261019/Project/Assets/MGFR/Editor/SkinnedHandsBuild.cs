using System;
using UnityEditor;
using UnityEngine;

namespace MGFR.BareHands
{
 public static class SkinnedHandsBuild
 {
  public static void Build()
  {
   foreach(string name in new[]{"LeftHand","RightHand"})
   {
    string path="Assets/MGFR/Resources/BareHands/"+name+".fbx";
    var importer=(ModelImporter)AssetImporter.GetAtPath(path);importer.isReadable=true;importer.SaveAndReimport();
    var model=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path));
    var shader=Shader.Find("MGFR/HandDepth");var material=new Material(shader);
    var mesh=new HandDepthMesh(name=="LeftHand"?0:1,material);
    var frame=new HandFrame{Tracked=true,ValidCount=26};
    for(int i=0;i<26;i++){frame.Valid[i]=true;frame.Joints[i]=new Pose(mesh.Bones[i].position,mesh.Bones[i].rotation);}
    mesh.FitSkin=false;mesh.Object.SetActive(true);
    var before=new Mesh();mesh.Renderer.BakeMesh(before);var original=before.vertices;
    mesh.Update(frame,true);var after=new Mesh();mesh.Renderer.BakeMesh(after);var current=after.vertices;
    float max=0;for(int i=0;i<original.Length;i++)max=Mathf.Max(max,Vector3.Distance(original[i],current[i]));
    if(max>.0001f)throw new Exception(name+" bind pose changed "+max);
    var turn=Quaternion.Euler(15,65,-20);var shift=new Vector3(.3f,1.1f,-.6f);
    for(int i=0;i<26;i++)frame.Joints[i]=new Pose(shift+turn*frame.Joints[i].position,turn*frame.Joints[i].rotation);
    mesh.Update(frame,true);
    for(int i=0;i<26;i++)if(Vector3.Distance(mesh.Bones[i].position,frame.Joints[i].position)>.00001f)throw new Exception(name+" joint mismatch "+i);
    mesh.FitSkin=true;mesh.Update(frame,true);
    for(int i=0;i<26;i++)if(Vector3.Distance(mesh.Bones[i].position,frame.Joints[i].position)>.00001f)throw new Exception("Skin fitting moved a joint");
    mesh.Update(frame,false);if(mesh.Object.activeSelf)throw new Exception("Tracking loss must hide mesh");
    Debug.Log($"[MGFR skinned hand check] {name} PASS joints=26 bindError={max} vertices={mesh.Mesh.vertexCount} rawPoseMapping=True trackingLossHides=True");
    UnityEngine.Object.DestroyImmediate(model);UnityEngine.Object.DestroyImmediate(mesh.Object);UnityEngine.Object.DestroyImmediate(mesh.Mesh);
    UnityEngine.Object.DestroyImmediate(before);UnityEngine.Object.DestroyImmediate(after);UnityEngine.Object.DestroyImmediate(material);
   }
   HandsBuild.Build();
  }
 }
}
