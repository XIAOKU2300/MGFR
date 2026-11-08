using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

[Serializable] public class EnfNode {public string name,path;public int parent;public float[] t,q,s;}
[Serializable] public class EnfSubmesh {public int first,count;}
[Serializable] public class EnfMesh {public string name,file;public int vertices,indexCount,boneCount;public int[] bones;public EnfSubmesh[] submeshes;}
[Serializable] public class EnfModel {public string name;public EnfNode[] nodes;public EnfMesh[] meshes;}
[Serializable] public class EnfMaterial {public string name,texture;public float[] color,scale,offset;public float cutoff;public bool transparent;}
[Serializable] public class EnfMaterials {public EnfMaterial[] materials;}
[Serializable] public class EnfClip {public string name,label,file;public int frames;public float fps,duration;public bool loop;}
[Serializable] public class EnfManifest {public EnfClip[] clips;}

public sealed class NativeMotionPlayer:MonoBehaviour {
 public Transform[] Bones; public EnfManifest Manifest; public EnfModel Model; public string AssetRoot,MotionRoot;
 public Camera ReviewCamera; public bool Playing=true; public int Current; public float TimeInClip;
 float[] values; int frames;float fps;Dictionary<string,Material> materialCache=new Dictionary<string,Material>();
 static Vector3 V(float[] v)=>new Vector3(v[0],v[1],v[2]);
 static Quaternion Q(float[] v)=>new Quaternion(v[0],v[1],v[2],v[3]);
 public void Build(string assetRoot,string motionRoot) {
  AssetRoot=assetRoot;MotionRoot=motionRoot;Model=JsonUtility.FromJson<EnfModel>(File.ReadAllText(Path.Combine(assetRoot,"native-model.json")));
  Manifest=JsonUtility.FromJson<EnfManifest>(File.ReadAllText(Path.Combine(motionRoot,"manifest.json")));
  var materials=JsonUtility.FromJson<EnfMaterials>(File.ReadAllText(Path.Combine(assetRoot,"preview-materials.json")));
  var shader=Shader.Find("EndfieldNative/Preview");if(shader==null)throw new Exception("Native preview shader missing");
  foreach(var data in materials.materials) {
   var m=new Material(shader){name=data.name};m.SetColor("_Color",data.color.Length>=4?new Color(data.color[0],data.color[1],data.color[2],data.color[3]):Color.white);
   if(!string.IsNullOrEmpty(data.texture)) {var tex=new Texture2D(2,2,TextureFormat.RGBA32,false);if(!tex.LoadImage(File.ReadAllBytes(Path.Combine(assetRoot,data.texture))))throw new Exception("Texture decode failed");m.mainTexture=tex;}
   m.mainTextureScale=new Vector2(data.scale[0],data.scale[1]);m.mainTextureOffset=new Vector2(data.offset[0],data.offset[1]);
   m.SetFloat("_Cutoff",data.cutoff);m.SetInt("_Src",data.transparent?5:1);m.SetInt("_Dst",data.transparent?10:0);m.renderQueue=data.transparent?3000:2000;
   materialCache.Add(data.name,m);
  }
  Bones=new Transform[Model.nodes.Length];for(int i=0;i<Bones.Length;i++)Bones[i]=new GameObject(Model.nodes[i].name).transform;
  for(int i=0;i<Bones.Length;i++){var n=Model.nodes[i];Bones[i].SetParent(n.parent<0?transform:Bones[n.parent],false);Bones[i].localPosition=V(n.t);Bones[i].localRotation=Q(n.q);Bones[i].localScale=V(n.s);}
  int renderers=0;
  foreach(var data in Model.meshes) {
   if(data.name.Contains("shadow")||data.name.Contains("cloth_05")||data.name.Contains("cloth_06")||data.name.Contains("cloth_07")||data.name.Contains("cloth_08")||data.name.Contains("cloth_09"))continue;
   var mesh=new Mesh(){name=data.name,indexFormat=IndexFormat.UInt32};
   using(var reader=new BinaryReader(File.OpenRead(Path.Combine(assetRoot,data.file)))) {
    Vector3[] vertices=new Vector3[data.vertices],normals=new Vector3[data.vertices];Vector2[] uv=new Vector2[data.vertices];
    for(int i=0;i<data.vertices;i++)vertices[i]=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
    for(int i=0;i<data.vertices;i++)normals[i]=new Vector3(reader.ReadSingle(),reader.ReadSingle(),reader.ReadSingle());
    for(int i=0;i<data.vertices;i++)uv[i]=new Vector2(reader.ReadSingle(),reader.ReadSingle());
    var ids=new int[data.vertices,4];for(int i=0;i<data.vertices;i++)for(int j=0;j<4;j++)ids[i,j]=reader.ReadUInt16();
    var weights=new BoneWeight[data.vertices];for(int i=0;i<data.vertices;i++)weights[i]=new BoneWeight(){boneIndex0=ids[i,0],boneIndex1=ids[i,1],boneIndex2=ids[i,2],boneIndex3=ids[i,3],weight0=reader.ReadSingle(),weight1=reader.ReadSingle(),weight2=reader.ReadSingle(),weight3=reader.ReadSingle()};
    int[] indices=new int[data.indexCount];for(int i=0;i<indices.Length;i++)indices[i]=(int)reader.ReadUInt32();
    var binds=new Matrix4x4[data.boneCount];for(int b=0;b<binds.Length;b++){var m=new Matrix4x4();for(int row=0;row<4;row++)for(int col=0;col<4;col++)m[row,col]=reader.ReadSingle();binds[b]=m;}
    if(reader.BaseStream.Position!=reader.BaseStream.Length)throw new Exception("Mesh bytes not consumed: "+data.name);
    mesh.vertices=vertices;mesh.normals=normals;mesh.uv=uv;mesh.boneWeights=weights;mesh.bindposes=binds;mesh.subMeshCount=data.submeshes.Length;
    for(int i=0;i<data.submeshes.Length;i++){var sub=data.submeshes[i];var tri=new int[sub.count];Array.Copy(indices,sub.first,tri,0,tri.Length);mesh.SetTriangles(tri,i);}
   }
   var renderer=new GameObject(data.name).AddComponent<SkinnedMeshRenderer>();renderer.transform.SetParent(transform,false);renderer.sharedMesh=mesh;renderer.bones=Array.ConvertAll(data.bones,b=>Bones[b]);renderer.rootBone=Bones[0];renderer.localBounds=new Bounds(new Vector3(0,.9f,0),new Vector3(4,4,4));renderer.updateWhenOffscreen=true;
   string key="M"+data.name.Substring(1).Replace("_lod0","");if(!materialCache.TryGetValue(key,out var material))throw new Exception("Material missing "+key);
   var slots=new Material[data.submeshes.Length];for(int i=0;i<slots.Length;i++)slots[i]=material;renderer.sharedMaterials=slots;renderers++;
  }
  Debug.Log($"[Endfield native] {Bones.Length} original nodes; {renderers} original LOD0 renderers; {Manifest.clips.Length} clips; no PMX/MGFR rig");
  Load(0);
 }
 public void Load(int index) {
  Current=(index+Manifest.clips.Length)%Manifest.clips.Length;TimeInClip=0;
  using(var reader=new BinaryReader(File.OpenRead(Path.Combine(MotionRoot,Manifest.clips[Current].file)))) {
   if(System.Text.Encoding.ASCII.GetString(reader.ReadBytes(8))!="ENFMOT1\0")throw new Exception("Motion magic");int count=reader.ReadInt32();frames=reader.ReadInt32();fps=reader.ReadSingle();if(count!=Bones.Length)throw new Exception("Motion/skeleton mismatch");
   byte[] bytes=reader.ReadBytes(checked(frames*count*40));values=new float[bytes.Length/4];Buffer.BlockCopy(bytes,0,values,0,bytes.Length);if(bytes.Length!=frames*count*40)throw new Exception("Motion truncated");
  }
  Apply(0);
 }
 public void Apply(float seconds) {
  TimeInClip=Mathf.Clamp(seconds,0,(frames-1)/fps);float cursor=TimeInClip*fps;int a=Mathf.FloorToInt(cursor),b=Mathf.Min(a+1,frames-1);float blend=cursor-a;
  for(int i=0;i<Bones.Length;i++) {int x=(a*Bones.Length+i)*10,y=(b*Bones.Length+i)*10;
   Bones[i].localRotation=Quaternion.Slerp(new Quaternion(values[x],values[x+1],values[x+2],values[x+3]),new Quaternion(values[y],values[y+1],values[y+2],values[y+3]),blend);
   Bones[i].localPosition=Vector3.Lerp(new Vector3(values[x+4],values[x+5],values[x+6]),new Vector3(values[y+4],values[y+5],values[y+6]),blend);
   Bones[i].localScale=Vector3.Lerp(new Vector3(values[x+7],values[x+8],values[x+9]),new Vector3(values[y+7],values[y+8],values[y+9]),blend);
  }
 }
 void Update(){if(values==null)return;if(Input.GetKeyDown(KeyCode.RightArrow))Load(Current+1);if(Input.GetKeyDown(KeyCode.LeftArrow))Load(Current-1);if(Input.GetKeyDown(KeyCode.Space))Playing=!Playing;if(Input.GetKeyDown(KeyCode.Escape))Application.Quit();if(Playing){float next=TimeInClip+Time.deltaTime;if(next>Manifest.clips[Current].duration)next=0;Apply(next);}}
 void OnGUI(){if(Manifest==null)return;GUILayout.BeginArea(new Rect(16,16,330,Screen.height-32),GUI.skin.box);GUILayout.Label("Endfield native / Si motion preview");GUILayout.Label((Current+1)+" / "+Manifest.clips.Length+"  "+Manifest.clips[Current].label);GUILayout.Label("Left/Right: switch  Space: pause  Esc: exit");GUILayout.Label(TimeInClip.ToString("F2")+" / "+Manifest.clips[Current].duration.ToString("F2")+" s");float seek=GUILayout.HorizontalSlider(TimeInClip,0,Manifest.clips[Current].duration);if(Mathf.Abs(seek-TimeInClip)>.01f)Apply(seek);for(int i=0;i<Manifest.clips.Length;i++)if(GUILayout.Button(Manifest.clips[i].label))Load(i);GUILayout.EndArea();}
}
