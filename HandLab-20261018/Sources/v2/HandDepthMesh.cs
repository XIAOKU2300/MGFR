using UnityEngine;
using UnityEngine.Rendering;

namespace MGFR.BareHands
{
 public sealed class HandDepthMesh
 {
  public static readonly int[,] Segments={{2,3},{3,4},{4,5},{6,7},{7,8},{8,9},{9,10},
   {11,12},{12,13},{13,14},{14,15},{16,17},{17,18},{18,19},{19,20},{21,22},{22,23},{23,24},{24,25}};
  const int Sides=8,Rings=6,SegmentVertices=Sides*Rings;
  public readonly GameObject Object;public readonly Mesh Mesh;
  readonly Vector3[] vertices=new Vector3[19*SegmentVertices+8];
  public HandDepthMesh(int hand,Material material)
  {
   Object=new GameObject("Real hand depth "+hand);Object.AddComponent<MeshFilter>();
   var renderer=Object.AddComponent<MeshRenderer>();renderer.sharedMaterial=material;renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=false;
   Mesh=new Mesh{name="Joint-fitted hand occluder"};Mesh.MarkDynamic();
   var triangles=new int[19*(Rings-1)*Sides*6+36];int index=0;
   for(int s=0;s<19;s++)for(int r=0;r<Rings-1;r++)for(int a=0;a<Sides;a++)
   {
    int p=s*SegmentVertices+r*Sides+a,q=s*SegmentVertices+r*Sides+(a+1)%Sides;
    triangles[index++]=p;triangles[index++]=q;triangles[index++]=p+Sides;
    triangles[index++]=q;triangles[index++]=q+Sides;triangles[index++]=p+Sides;
   }
   int start=19*SegmentVertices;int[] box={0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7};
   foreach(int v in box)triangles[index++]=start+v;
   Mesh.vertices=vertices;Mesh.triangles=triangles;Object.GetComponent<MeshFilter>().sharedMesh=Mesh;Object.SetActive(false);
  }
  public static void PalmShape(HandFrame f,out Vector3 center,out Quaternion rotation,out Vector3 size)
  {
   var knuckles=(f.Joints[7].position+f.Joints[12].position+f.Joints[17].position+f.Joints[22].position)*.25f;
   var wrist=f.Joints[1].position;var along=(knuckles-wrist).normalized;
   var across=(f.Joints[7].position-f.Joints[22].position).normalized;
   var normal=Vector3.Cross(across,along).normalized;
   rotation=Quaternion.LookRotation(normal,along);center=(wrist+knuckles)*.5f;
   size=new Vector3(Vector3.Distance(f.Joints[7].position,f.Joints[22].position)+.013f*f.Scale,Vector3.Distance(wrist,knuckles)+.012f*f.Scale,.022f*f.Scale);
  }
  public void Update(HandFrame f,bool show)
  {
   Object.SetActive(show&&f.Tracked);if(!Object.activeSelf)return;
   for(int s=0;s<19;s++)
   {
    int a=Segments[s,0],b=Segments[s,1],offset=s*SegmentVertices;
    if(!f.Valid[a]||!f.Valid[b]){for(int k=0;k<SegmentVertices;k++)vertices[offset+k]=f.Joints[0].position;continue;}
    Vector3 p=f.Joints[a].position,q=f.Joints[b].position,axis=(q-p).normalized;
    float radius=Mathf.Clamp((f.Radius[a]+f.Radius[b])*.5f,.005f,.017f);
    Vector3 right=Vector3.Cross(axis,Mathf.Abs(axis.y)>.9f?Vector3.right:Vector3.up).normalized,up=Vector3.Cross(axis,right);
    for(int ring=0;ring<Rings;ring++)
    {
     float axial=ring==0?-1:ring==1?-.7071f:ring==4?.7071f:ring==5?1:0;
     float radial=ring==0||ring==5?0:ring==1||ring==4?.7071f:1;
     Vector3 center=(ring<3?p:q)+axis*(axial*radius);
     for(int side=0;side<Sides;side++)
     {
      float theta=side*Mathf.PI*2/Sides;
      vertices[offset+ring*Sides+side]=center+(right*Mathf.Cos(theta)+up*Mathf.Sin(theta))*radius*radial;
     }
    }
   }
   PalmShape(f,out var palm,out var rotation,out var size);
   for(int corner=0;corner<8;corner++)
   {
    int planar=corner%4;float x=planar==1||planar==2?1:-1,y=planar>=2?1:-1,z=corner>=4?1:-1;
    vertices[19*SegmentVertices+corner]=palm+rotation*Vector3.Scale(new Vector3(x,y,z),size*.5f);
   }
   Mesh.vertices=vertices;Mesh.RecalculateBounds();
  }
 }
}
