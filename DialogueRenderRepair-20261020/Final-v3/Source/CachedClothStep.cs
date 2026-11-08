using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;
using MGFR.Skins.ClothPhysics;

namespace MGFR.StructuredVoiceFinal {
 // Same XPBD equations, substeps, constraints, grips and contact order as the
 // installed solver. Only immutable topology and per-step capsule math are cached.
 public sealed class CachedClothStep {
  struct Link {public int a,b;public float rest,compliance,lambda;}
  struct Shape {public Vector3 a,axis,min,max;public float radius,inverseLength;}
  readonly SwimsuitClothSolver solver;
  readonly Link[] links;
  readonly float scale;
  readonly int[] influences,groups;
  readonly float[] weights;
  readonly Vector3[] rest;
  readonly Action<float> maximumOffset;
  readonly Action<int> contacts;
  Shape[] bodyShapes=new Shape[32];readonly Shape[][] handShapes={new Shape[32],new Shape[32]};
  int contactCount;
  public Bounds Bounds {get;private set;}
  static readonly BindingFlags Flags=BindingFlags.Instance|BindingFlags.NonPublic;
  public SwimsuitClothSolver Solver=>solver;
  public CachedClothStep(SwimsuitClothSolver value){
   solver=value;var type=typeof(SwimsuitClothSolver);
   scale=(float)type.GetField("scale",Flags).GetValue(value);
   var source=(IEnumerable)type.GetField("links",Flags).GetValue(value);
   var data=new List<Link>();
   foreach(var item in source){var t=item.GetType();data.Add(new Link{a=(int)t.GetField("a").GetValue(item),b=(int)t.GetField("b").GetValue(item),rest=(float)t.GetField("rest").GetValue(item),compliance=(float)t.GetField("compliance").GetValue(item)});}
   links=data.ToArray();
   var indices=(int[,])type.GetField("influence",Flags).GetValue(value);
   var originalWeights=(float[,])type.GetField("weights",Flags).GetValue(value);
   rest=(Vector3[])type.GetField("renderRest",Flags).GetValue(value);
   influences=new int[rest.Length*4];weights=new float[influences.Length];groups=new int[rest.Length];
   for(int i=0;i<rest.Length;i++){groups[i]=value.RenderGroupForVertex(i);for(int k=0;k<4;k++){influences[i*4+k]=indices[i,k];weights[i*4+k]=originalWeights[i,k];}}
   maximumOffset=(Action<float>)Delegate.CreateDelegate(typeof(Action<float>),value,type.GetProperty("MaximumOffset").GetSetMethod(true));
   contacts=(Action<int>)Delegate.CreateDelegate(typeof(Action<int>),value,type.GetProperty("Contacts").GetSetMethod(true));
  }
  static int Cache(List<SwimsuitClothSolver.Capsule> input,ref Shape[] result){
   if(result.Length<input.Count)Array.Resize(ref result,Math.Max(input.Count,result.Length*2));
   for(int i=0;i<input.Count;i++){var c=input[i];var d=c.b-c.a;var margin=Vector3.one*c.radius;result[i]=new Shape{a=c.a,axis=d,min=Vector3.Min(c.a,c.b)-margin,max=Vector3.Max(c.a,c.b)+margin,radius=c.radius,inverseLength=d.sqrMagnitude>1e-10f?1/d.sqrMagnitude:0};}
   return input.Count;
  }
  void Project(ref SwimsuitClothSolver.Particle p,ref Shape shape){
   var v=p.position;
   if(v.x<shape.min.x||v.x>shape.max.x||v.y<shape.min.y||v.y>shape.max.y||v.z<shape.min.z||v.z>shape.max.z)return;
   float t=Mathf.Clamp01(Vector3.Dot(v-shape.a,shape.axis)*shape.inverseLength);
   var point=shape.a+shape.axis*t;var normal=v-point;float squared=normal.sqrMagnitude;
   if(squared>=shape.radius*shape.radius||squared<1e-14f)return;
   normal/=Mathf.Sqrt(squared);var movement=p.position-p.previous;
   var correction=point+normal*shape.radius-p.position;p.position+=correction;
   p.previous+=correction+normal*Mathf.Min(0,Vector3.Dot(movement,normal));contactCount++;
  }
  public void Step(float delta,List<SwimsuitClothSolver.Capsule> body,List<SwimsuitClothSolver.Capsule>[] hands,Vector3 wind){
   int steps=Mathf.Clamp(Mathf.CeilToInt(delta*90),1,2);float dt=Mathf.Clamp(delta,.001f,.0222f)/steps;
   int bodies=Cache(body,ref bodyShapes),left=Cache(hands[0],ref handShapes[0]),right=Cache(hands[1],ref handShapes[1]);
   var particles=solver.Particles;var enabled=solver.EnabledGroups;var grips=solver.Grips;
   contactCount=0;float maxOffset=0,decay=Mathf.Exp(-3.5f*dt),dtSquared=dt*dt;
   var acceleration=(Vector3.down*9.81f+wind)*dtSquared;
   for(int step=0;step<steps;step++){
    for(int i=0;i<links.Length;i++)links[i].lambda=0;
    for(int i=0;i<particles.Length;i++){
     ref var p=ref particles[i];
     if(!enabled[p.group]||p.inverseMass==0){p.position=p.previous=p.target;continue;}
     var velocity=(p.position-p.previous)*decay;p.previous=p.position;p.position+=velocity+acceleration;
    }
    for(int iteration=0;iteration<4;iteration++){
     for(int i=0;i<links.Length;i++){
      ref var link=ref links[i];ref var a=ref particles[link.a];ref var b=ref particles[link.b];
      if(!enabled[a.group])continue;
      var difference=a.position-b.position;float length=difference.magnitude,sum=a.inverseMass+b.inverseMass;
      if(length<1e-8f||sum<=0)continue;
      float alpha=link.compliance/dtSquared,dl=(-(length-link.rest)-alpha*link.lambda)/(sum+alpha);
      var correction=difference*(dl/length);a.position+=correction*a.inverseMass;b.position-=correction*b.inverseMass;link.lambda+=dl;
     }
     for(int i=0;i<particles.Length;i++){
      ref var p=ref particles[i];if(!enabled[p.group]||p.inverseMass==0)continue;
      var offset=p.position-p.target;if(offset.sqrMagnitude>p.travel*p.travel)p.position=p.target+Vector3.ClampMagnitude(offset,p.travel);
      for(int c=0;c<bodies;c++)Project(ref p,ref bodyShapes[c]);
      for(int h=0;h<2;h++){
       bool heldNearby=grips[h].particle>=0&&(p.position-particles[grips[h].particle].position).sqrMagnitude<.002f*scale*scale;
       int count=h==0?left:right;
       if(!heldNearby&&count>0&&(p.position-hands[h][count-1].a).sqrMagnitude<.24f*.24f)
        for(int c=0;c<count;c++)Project(ref p,ref handShapes[h][c]);
      }
     }
     for(int h=0;h<2;h++)if(grips[h].particle>=0){
      ref var p=ref particles[grips[h].particle];var target=p.target+Vector3.ClampMagnitude(grips[h].target-p.target,p.travel);
      p.position=Vector3.Lerp(p.position,target,.82f);
     }
    }
    for(int i=0;i<particles.Length;i++){
     ref var p=ref particles[i];var velocity=Vector3.ClampMagnitude((p.position-p.previous)/dt,2.5f);
     p.previous=p.position-velocity*dt;maxOffset=Mathf.Max(maxOffset,Vector3.Distance(p.position,p.target));
    }
   }
   maximumOffset(maxOffset);contacts(contactCount);
  }
  public void WriteVertices(Matrix4x4[] drivers,Matrix4x4 worldToLocal,Vector3[] output){
   Vector3 min=new Vector3(float.PositiveInfinity,float.PositiveInfinity,float.PositiveInfinity),max=-min;
   var particles=solver.Particles;
   for(int i=0;i<output.Length;i++){
    var position=drivers[groups[i]].MultiplyPoint3x4(rest[i]);int start=i*4;
    for(int k=0;k<4;k++){ref var p=ref particles[influences[start+k]];position+=(p.position-p.target)*weights[start+k];}
    var v=worldToLocal.MultiplyPoint3x4(position);output[i]=v;min=Vector3.Min(min,v);max=Vector3.Max(max,v);
   }
   Bounds=new Bounds((min+max)*.5f,max-min);
  }
 }
}
