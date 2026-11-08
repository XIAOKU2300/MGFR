using UnityEngine;
using UnityEngine.Rendering;

namespace MGFR.BareHands
{
 // A metric envelope from the tracked skeleton, independent of FBX proportions.
 // All points are supplied in world metres. No extrapolation of SDK prediction.
 public sealed class HandOcclusionEnvelope
 {
  const int Sides=12,Rings=8,SegmentVertices=Sides*Rings,Segments=20;
  public readonly GameObject Object;
  public readonly Mesh Mesh;
  readonly Vector3[] vertices=new Vector3[Segments*SegmentVertices+14];
  readonly int[] indices=new int[Segments*(Rings-1)*Sides*6+72];
  readonly float[] radii=new float[26];
  readonly Vector3[] outline=new Vector3[6];
  double previousTime;
  bool initialized;
  public float PalmWidth {get;private set;}
  readonly int handIndex;
  readonly bool legacy=System.Array.IndexOf(System.Environment.GetCommandLineArgs(),"-mgfr-hand-envelope-original")>=0;
  public HandOcclusionEnvelope(Material material,int hand=0)
  {
   handIndex=hand;
   Object=new GameObject("Metric hand occlusion envelope");
   Mesh=new Mesh{name="Joint radius hand envelope"};Mesh.MarkDynamic();
   Object.AddComponent<MeshFilter>().sharedMesh=Mesh;
   var renderer=Object.AddComponent<MeshRenderer>();renderer.sharedMaterial=material;
   renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=false;
   int n=0;
   for(int s=0;s<Segments;s++)for(int r=0;r<Rings-1;r++)for(int k=0;k<Sides;k++)
   {
    int a=s*SegmentVertices+r*Sides+k,b=s*SegmentVertices+r*Sides+(k+1)%Sides;
    indices[n++]=a;indices[n++]=a+Sides;indices[n++]=b;
    indices[n++]=b;indices[n++]=a+Sides;indices[n++]=b+Sides;
   }
   int start=Segments*SegmentVertices;
   for(int k=0;k<6;k++)
   {
    int a=start+k,b=start+(k+1)%6;
    indices[n++]=start+12;indices[n++]=a;indices[n++]=b;
    indices[n++]=start+13;indices[n++]=b+6;indices[n++]=a+6;
    indices[n++]=a;indices[n++]=a+6;indices[n++]=b;
    indices[n++]=b;indices[n++]=a+6;indices[n++]=b+6;
   }
   Mesh.vertices=vertices;Mesh.triangles=indices;Object.SetActive(false);
  }
  public void Update(HandFrame f,bool show,int layer,double now)
  {
   bool active=show&&f.Tracked&&f.Valid[1];
   Object.SetActive(active);Object.layer=layer;
   if(!active){initialized=false;return;}
   float dt=initialized?Mathf.Clamp((float)(now-previousTime),0,.05f):0;
   previousTime=now;
   float alpha=initialized?1-Mathf.Exp(-dt*5):1;
   for(int i=0;i<26;i++)if(f.Valid[i])
   {
    float radius=Mathf.Clamp(f.Radius[i],.004f,.025f);
    if(!initialized||radii[i]==0)radii[i]=radius;
    else if(f.Observed[i]&&radius>radii[i]*.65f&&radius<radii[i]*1.5f)radii[i]=Mathf.Lerp(radii[i],radius,alpha);
   }
   initialized=true;
   // Segment-specific thickness follows the user's anatomy. Missing segments
   // collapse, rather than leaving stale vertices from a previous hand pose.
   for(int s=0;s<Segments;s++)
   {
    int a=s<19?HandDepthMesh.Segments[s,0]:1,b=s<19?HandDepthMesh.Segments[s,1]:2;
    Vector3 p=f.Joints[a].position,q=f.Joints[b].position;
    if(s==19)p=Vector3.Lerp(f.Joints[1].position,f.Joints[0].position,.4f);
    if(!f.Valid[a]||!f.Valid[b])
    {for(int k=0;k<SegmentVertices;k++)vertices[s*SegmentVertices+k]=f.Joints[1].position;continue;}
    Vector3 axis=(q-p).normalized;
    if(axis.sqrMagnitude<.5f)axis=Vector3.up;
    Vector3 x=Vector3.Cross(axis,Mathf.Abs(axis.y)<.9f?Vector3.up:Vector3.right).normalized;
    Vector3 z=Vector3.Cross(axis,x);
    // Slightly conservative silhouette, with a bounded metric inset instead
    // of multiplying the entire hand about the wrist.
    float ra=Mathf.Max(.003f,radii[a]-.0007f),rb=Mathf.Max(.003f,radii[b]-.0007f);
    if(s==19)ra=rb=Mathf.Clamp(Vector3.Distance(f.Joints[7].position,f.Joints[22].position)*.18f,.008f,.022f);
    for(int r=0;r<Rings;r++)
    {
     bool first=r<4;float angle=(first?r:r-4)*Mathf.PI/6;
     bool tip=b==5||b==10||b==15||b==20||b==25;
     float extension=legacy?rb:tip?Mathf.Min(rb*.25f,.002f)*HandVisualCalibration.Settings(handIndex).tipLength[HandVisualCalibration.Finger(b)]:rb*.45f;
     float axial=first?-Mathf.Cos(angle)*(legacy?ra:ra*.45f):Mathf.Sin(angle)*extension;
     float radial=first?Mathf.Sin(angle)*ra:Mathf.Cos(angle)*(legacy?rb:Mathf.Min(rb,ra*.94f));
     Vector3 center=(first?p:q)+axis*axial;
     for(int k=0;k<Sides;k++)
     {float t=k*2*Mathf.PI/Sides;vertices[s*SegmentVertices+r*Sides+k]=center+radial*(Mathf.Cos(t)*x+Mathf.Sin(t)*z);}
    }
   }
   if(!f.Valid[0]||!f.Valid[7]||!f.Valid[12]||!f.Valid[17]||!f.Valid[22])
   {for(int k=Segments*SegmentVertices;k<vertices.Length;k++)vertices[k]=f.Joints[1].position;Mesh.vertices=vertices;Mesh.RecalculateBounds();return;}
   var wrist=f.Joints[1].position;var left=f.Joints[7].position;var right=f.Joints[22].position;
   var across=(right-left).normalized;var along=((left+right)*.5f-wrist).normalized;
   var normal=Vector3.Cross(across,along).normalized;
   if(normal.sqrMagnitude<.5f)normal=f.Joints[1].rotation*Vector3.forward;
   PalmWidth=Vector3.Distance(left,right);
   var calibration=HandVisualCalibration.Settings(handIndex);
   float halfThickness=Mathf.Clamp(radii[0]*.65f,.008f,.020f)*calibration.palmThickness;
   outline[0]=wrist-across*PalmWidth*.36f;
   outline[1]=left-across*radii[7]*.65f;
   outline[2]=f.Joints[12].position;
   outline[3]=f.Joints[17].position;
   outline[4]=right+across*radii[22]*.65f;
   outline[5]=wrist+across*PalmWidth*.36f;
   var midpoint=(left+right)*.5f;
   for(int k=0;k<6;k++){var d=outline[k]-midpoint;outline[k]+=across*Vector3.Dot(d,across)*(calibration.palmWidth-1);}
   Vector3 centerPalm=Vector3.zero;int start=Segments*SegmentVertices;
   for(int k=0;k<6;k++)
   {vertices[start+k]=outline[k]+normal*halfThickness;vertices[start+k+6]=outline[k]-normal*halfThickness;centerPalm+=outline[k]/6;}
   vertices[start+12]=centerPalm+normal*halfThickness;vertices[start+13]=centerPalm-normal*halfThickness;
   Mesh.vertices=vertices;Mesh.RecalculateBounds();
  }
  public void Dispose(){UnityEngine.Object.Destroy(Mesh);UnityEngine.Object.Destroy(Object);}
 }
}
