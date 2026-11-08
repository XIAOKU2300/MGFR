using System;
using System.Collections.Generic;
using UnityEngine;
using MGFR.PhysicsRig;

namespace MGFR.BareHands
{
 // Refit a fixed-topology BVH against the current skinned garment. Both hands
 // share one bake per frame; a pinch searches the visible surface, not proxies.
 public sealed class HandSurfaceQuery
 {
  readonly PmxSecondaryPhysics physics;
  readonly SkinnedMeshRenderer renderer;
  readonly Mesh baked=new Mesh();
  readonly List<Vector3> vertices=new List<Vector3>();
  readonly BoneWeight[] weights;
  readonly int[] triangles,boneBody;
  readonly int[] candidates=new int[12]; readonly float[] scores=new float[12];
  readonly List<Node> nodes=new List<Node>();
  readonly int[] eligible; readonly Vector3[] centroids;
  int count,cachedFrame=-1;
  public int LastTrianglesTested {get;private set;}
  public int EligibleTriangles=>eligible.Length;
  struct Node {public Bounds bounds;public int first,count,left,right;}
  sealed class Compare: IComparer<int>
  {
   public Vector3[] points;public int axis;
   public int Compare(int a,int b)=>points[a][axis].CompareTo(points[b][axis]);
  }
  public HandSurfaceQuery(PmxSecondaryPhysics physics)
  {
   this.physics=physics;renderer=physics.Loader.Renderer;
   var mesh=renderer.sharedMesh;weights=mesh.boneWeights;triangles=mesh.triangles;
   boneBody=new int[renderer.bones.Length];Array.Fill(boneBody,-1);
   for(int i=0;i<physics.Bodies.Length;i++)
   {var d=physics.Data.bodies[i];if(!physics.Bodies[i].isKinematic&&d.group>=4&&d.group<=10)boneBody[d.bone]=i;}
   var pinned=new bool[boneBody.Length];
   for(int i=0;i<physics.Bodies.Length;i++)if(physics.Bodies[i].isKinematic)pinned[physics.Data.bodies[i].bone]=true;
   for(int i=0;i<boneBody.Length;i++)if(boneBody[i]<0&&!pinned[i])
    for(int p=physics.Loader.Data.bones[i].parent;p>=0;p=physics.Loader.Data.bones[p].parent)
    {if(pinned[p])break;if(boneBody[p]>=0){boneBody[i]=boneBody[p];break;}}
   var list=new List<int>();centroids=new Vector3[triangles.Length/3];var rest=mesh.vertices;
   for(int t=0;t<triangles.Length;t+=3)
   {
    if(Coverage(weights[triangles[t]])+Coverage(weights[triangles[t+1]])+Coverage(weights[triangles[t+2]])<=.75f)continue;
    list.Add(t/3);centroids[t/3]=(rest[triangles[t]]+rest[triangles[t+1]]+rest[triangles[t+2]])/3;
   }
   eligible=list.ToArray();if(eligible.Length>0)Build(0,eligible.Length);
  }
  int Build(int first,int length)
  {
   int id=nodes.Count;nodes.Add(default);
   var bounds=new Bounds(centroids[eligible[first]],Vector3.zero);
   for(int i=first+1;i<first+length;i++)bounds.Encapsulate(centroids[eligible[i]]);
   var node=new Node{first=first,count=length,left=-1,right=-1};
   if(length>12)
   {
    var size=bounds.size;int axis=size.x>=size.y&&size.x>=size.z?0:size.y>=size.z?1:2;
    Array.Sort(eligible,first,length,new Compare{points=centroids,axis=axis});
    int half=length/2;node.left=Build(first,half);node.right=Build(first+half,length-half);node.count=0;
   }
   nodes[id]=node;return id;
  }
  Bounds Refit(int id)
  {
   var n=nodes[id];Bounds bounds;
   if(n.left>=0){bounds=Refit(n.left);bounds.Encapsulate(Refit(n.right));}
   else
   {
    int t=eligible[n.first]*3;bounds=new Bounds(vertices[triangles[t]],Vector3.zero);
    for(int i=n.first;i<n.first+n.count;i++)
    {t=eligible[i]*3;bounds.Encapsulate(vertices[triangles[t]]);bounds.Encapsulate(vertices[triangles[t+1]]);bounds.Encapsulate(vertices[triangles[t+2]]);}
   }
   n.bounds=bounds;nodes[id]=n;return bounds;
  }
  float Weight(int bone,float value)=>bone>=0&&bone<boneBody.Length&&boneBody[bone]>=0?value:0;
  float Coverage(BoneWeight w)=>Weight(w.boneIndex0,w.weight0)+Weight(w.boneIndex1,w.weight1)+Weight(w.boneIndex2,w.weight2)+Weight(w.boneIndex3,w.weight3);
  void Add(int bone,float value,int exclude)
  {
   if(bone<0||bone>=boneBody.Length)return;
   int id=boneBody[bone];if(id<0||id==exclude||value<=0)return;
   for(int i=0;i<count;i++)if(candidates[i]==id){scores[i]+=value;return;}
   candidates[count]=id;scores[count++]=value;
  }
  void Add(BoneWeight w,float value,int exclude)
  {Add(w.boneIndex0,w.weight0*value,exclude);Add(w.boneIndex1,w.weight1*value,exclude);Add(w.boneIndex2,w.weight2*value,exclude);Add(w.boneIndex3,w.weight3*value,exclude);}
  public bool Find(Vector3 worldPoint,float reach,int exclude,out int body,out Vector3 modelPoint)
  {
   body=-1;modelPoint=Vector3.zero;LastTrianglesTested=0;
   if(reach<=0||eligible.Length==0)return false;
   var bounds=renderer.bounds;bounds.Expand(reach*2);if(!bounds.Contains(worldPoint))return false;
   if(cachedFrame!=Time.frameCount)
   {renderer.BakeMesh(baked);baked.GetVertices(vertices);Refit(0);cachedFrame=Time.frameCount;}
   // BakeMesh returns renderer-local vertices. This project uses uniform scale.
   var tr=renderer.transform;var p=tr.InverseTransformPoint(worldPoint);
   float scale=Mathf.Max(.0001f,Mathf.Abs(tr.lossyScale.x));float best=reach*reach/(scale*scale);
   Vector3 hit=Vector3.zero;Search(0,p,exclude,ref best,ref body,ref hit);
   if(body>=0)modelPoint=physics.Loader.transform.InverseTransformPoint(tr.TransformPoint(hit));
   return body>=0;
  }
  void Search(int id,Vector3 p,int exclude,ref float best,ref int body,ref Vector3 hit)
  {
   var n=nodes[id];if(n.bounds.SqrDistance(p)>best)return;
   if(n.left>=0)
   {
    int near=n.left,far=n.right;
    if(nodes[far].bounds.SqrDistance(p)<nodes[near].bounds.SqrDistance(p)){int swap=near;near=far;far=swap;}
    Search(near,p,exclude,ref best,ref body,ref hit);Search(far,p,exclude,ref best,ref body,ref hit);return;
   }
   for(int i=n.first;i<n.first+n.count;i++)
   {
    int t=eligible[i]*3,ia=triangles[t],ib=triangles[t+1],ic=triangles[t+2];
    LastTrianglesTested++;
    var q=ClosestTriangle(p,vertices[ia],vertices[ib],vertices[ic],out var bary);float distance=(q-p).sqrMagnitude;
    if(distance>best)continue;
    count=0;Add(weights[ia],bary.x,exclude);Add(weights[ib],bary.y,exclude);Add(weights[ic],bary.z,exclude);
    float total=0,largest=0;int selected=-1;
    for(int k=0;k<count;k++){total+=scores[k];if(scores[k]>largest){largest=scores[k];selected=candidates[k];}}
    if(total<.5f||selected<0)continue;
    best=distance;body=selected;hit=q;
   }
  }
  public bool FindSwept(Vector3 from,Vector3 to,float reach,int exclude,out int body,out Vector3 modelPoint)
  {
   // Never sweep across a tracking discontinuity or turn a remote pinch into a ray grab.
   float length=Vector3.Distance(from,to);int steps=length<=.08f?Mathf.Clamp(Mathf.CeilToInt(length/Mathf.Max(.006f,reach)),1,8):1;
   for(int step=steps;step>=1;step--)
    if(Find(Vector3.Lerp(from,to,step/(float)steps),reach,exclude,out body,out modelPoint))return true;
   body=-1;modelPoint=Vector3.zero;return false;
  }
  public void Invalidate(){cachedFrame=-1;}
  public void Dispose(){UnityEngine.Object.Destroy(baked);}
  public static Vector3 ClosestTriangle(Vector3 p,Vector3 a,Vector3 b,Vector3 c,out Vector3 bary)
  {
   var ab=b-a;var ac=c-a;
   if(Vector3.Cross(ab,ac).sqrMagnitude<1e-16f)
   {
    float u=Segment(p,a,b,out var x),v=Segment(p,b,c,out var y),w=Segment(p,c,a,out var z);
    if((x-p).sqrMagnitude<=(y-p).sqrMagnitude&&(x-p).sqrMagnitude<=(z-p).sqrMagnitude){bary=new Vector3(1-u,u,0);return x;}
    if((y-p).sqrMagnitude<=(z-p).sqrMagnitude){bary=new Vector3(0,1-v,v);return y;}
    bary=new Vector3(w,0,1-w);return z;
   }
   var ap=p-a;float d1=Vector3.Dot(ab,ap),d2=Vector3.Dot(ac,ap);
   if(d1<=0&&d2<=0){bary=Vector3.right;return a;}
   var bp=p-b;float d3=Vector3.Dot(ab,bp),d4=Vector3.Dot(ac,bp);
   if(d3>=0&&d4<=d3){bary=Vector3.up;return b;}
   float vc=d1*d4-d3*d2;
   if(vc<=0&&d1>=0&&d3<=0){float v=d1/(d1-d3);bary=new Vector3(1-v,v,0);return a+v*ab;}
   var cp=p-c;float d5=Vector3.Dot(ab,cp),d6=Vector3.Dot(ac,cp);
   if(d6>=0&&d5<=d6){bary=Vector3.forward;return c;}
   float vb=d5*d2-d1*d6;
   if(vb<=0&&d2>=0&&d6<=0){float w=d2/(d2-d6);bary=new Vector3(1-w,0,w);return a+w*ac;}
   float va=d3*d6-d5*d4;
   if(va<=0&&(d4-d3)>=0&&(d5-d6)>=0){float w=(d4-d3)/((d4-d3)+(d5-d6));bary=new Vector3(0,1-w,w);return b+w*(c-b);}
   float denom=1/(va+vb+vc),v0=vb*denom,w0=vc*denom;bary=new Vector3(1-v0-w0,v0,w0);return a+ab*v0+ac*w0;
  }
  static float Segment(Vector3 p,Vector3 a,Vector3 b,out Vector3 hit)
  {var d=b-a;float t=d.sqrMagnitude>1e-16f?Mathf.Clamp01(Vector3.Dot(p-a,d)/d.sqrMagnitude):0;hit=a+t*d;return t;}
 }
}
