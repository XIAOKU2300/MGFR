using System;
using System.Collections.Generic;
using UnityEngine;

namespace MGFR.Skins.ClothPhysics
{
    // A coarse, welded XPBD mesh drives fine rendered vertices by displacement.
    // The body skin remains untouched; cloth attachment frames follow the rig.
    public sealed class SwimsuitClothSolver
    {
        public struct Particle
        {
            public Vector3 rest, position, previous, target;
            public int group;
            public float inverseMass, travel;
        }
        struct Link { public int a,b; public float rest, compliance, lambda; }
        public struct Capsule { public Vector3 a,b; public float radius; }
        public struct Grip
        {
            public int particle;
            public Vector3 offset, target;
        }
        public Particle[] Particles;
        public readonly Grip[] Grips = { new Grip {particle=-1}, new Grip {particle=-1} };
        readonly List<Link> links = new List<Link>();
        readonly HashSet<ulong> bendKeys = new HashSet<ulong>();
        readonly int[,] influence;
        readonly float[,] weights;
        readonly Vector3[] renderRest;
        readonly int[] renderGroup;
        readonly List<int>[] neighbours;
        readonly float scale;
        public int ConstraintCount => links.Count;
        public float MaximumOffset {get;private set;}
        public int GrabStarts {get;private set;}
        public int Contacts {get;private set;}

        public SwimsuitClothSolver(Vector3[] vertices, int[] ids, int[] triangles, float modelScale, Matrix4x4[] drivers)
        {
            scale = modelScale; renderRest = vertices; renderGroup = new int[vertices.Length];
            var bins = new Dictionary<Vector4Int,List<int>>();
            var sums = new List<Vector3>(); var counts = new List<int>(); var groups = new List<int>();
            var vertexParticle = new int[vertices.Length];
            const float spacing = .030f;
            for(int i=0;i<vertices.Length;i++)
            {
                int group = ids[i] < 64393 ? (vertices[i].x > 0 ? 0 : 1) : ids[i] < 67103 ? 2 : 3;
                renderGroup[i]=group;
                var p=vertices[i]; var key=new Vector4Int(group,Mathf.RoundToInt(p.x/spacing),Mathf.RoundToInt(p.y/spacing),Mathf.RoundToInt(p.z/spacing));
                if(!bins.TryGetValue(key,out var list))
                {
                    list=new List<int>{sums.Count}; bins.Add(key,list);
                    sums.Add(Vector3.zero);counts.Add(0);groups.Add(group);
                }
                int n=list[0]; sums[n]+=p;counts[n]++;vertexParticle[i]=n;
            }
            Particles=new Particle[sums.Count]; neighbours=new List<int>[sums.Count];
            for(int i=0;i<Particles.Length;i++)
            {
                var rest=sums[i]/counts[i]; int group=groups[i];
                float pinHeight=group<2?1.205f:group==2?1.235f:.875f;
                float distance=pinHeight-rest.y;
                float free=Mathf.Clamp01(distance/(group==2?.055f:.075f));
                if(free<.08f)free=0;
                float travel=(group==2?.065f:group==3?.24f:.28f)*free*scale;
                var world=drivers[group].MultiplyPoint3x4(rest);
                Particles[i]=new Particle{rest=rest,group=group,position=world,previous=world,target=world,inverseMass=free,travel=travel};
                neighbours[i]=new List<int>();
            }
            var edges=new HashSet<ulong>(); var across=new Dictionary<ulong,int>();
            for(int i=0;i<triangles.Length;i+=3)
            {
                int a=vertexParticle[triangles[i]],b=vertexParticle[triangles[i+1]],c=vertexParticle[triangles[i+2]];
                if(a==b||a==c||b==c)continue;
                AddEdge(a,b,2e-7f,edges);AddEdge(b,c,2e-7f,edges);AddEdge(c,a,2e-7f,edges);
                Bend(a,b,c,across);Bend(b,c,a,across);Bend(c,a,b,across);
            }
            // Sew disconnected flower/trim islands to nearby fabric, within the
            // same garment group. Never bridge the left/right sleeves or body.
            for(int n=0;n<Particles.Length;n++)
            {
                var p=Particles[n].rest; int group=Particles[n].group;
                var key=new Vector4Int(group,Mathf.RoundToInt(p.x/spacing),Mathf.RoundToInt(p.y/spacing),Mathf.RoundToInt(p.z/spacing));
                int connected=0;
                for(int x=-1;x<=1;x++)for(int y=-1;y<=1;y++)for(int z=-1;z<=1;z++)
                {
                    var near=new Vector4Int(group,key.x+x,key.y+y,key.z+z);
                    if(!bins.TryGetValue(near,out var list))continue;
                    int other=list[0];
                    if(other==n||(Particles[other].rest-p).sqrMagnitude>.00065f)continue;
                    if(AddEdge(n,other,2e-6f,edges)&&++connected>=4)break;
                }
            }
            influence=new int[vertices.Length,4];weights=new float[vertices.Length,4];
            for(int i=0;i<vertices.Length;i++)
            {
                int nearest=vertexParticle[i]; var choices=new List<int>{nearest};choices.AddRange(neighbours[nearest]);
                choices.Sort((a,b)=>(Particles[a].rest-vertices[i]).sqrMagnitude.CompareTo((Particles[b].rest-vertices[i]).sqrMagnitude));
                float total=0;
                for(int k=0;k<4;k++)
                {
                    int id=choices[Mathf.Min(k,choices.Count-1)];influence[i,k]=id;
                    float w=1f/Mathf.Max(.000003f,(Particles[id].rest-vertices[i]).sqrMagnitude);
                    weights[i,k]=w;total+=w;
                }
                for(int k=0;k<4;k++)weights[i,k]/=total;
            }
        }
        readonly struct Vector4Int : IEquatable<Vector4Int>
        {
            public readonly int group,x,y,z;
            public Vector4Int(int g,int x,int y,int z){group=g;this.x=x;this.y=y;this.z=z;}
            public bool Equals(Vector4Int b)=>group==b.group&&x==b.x&&y==b.y&&z==b.z;
            public override bool Equals(object b)=>b is Vector4Int v&&Equals(v);
            public override int GetHashCode()=>unchecked(group*73471^x*73856093^y*19349663^z*83492791);
        }
        static ulong Key(int a,int b)=>(ulong)(uint)Mathf.Min(a,b)<<32|(uint)Mathf.Max(a,b);
        bool AddEdge(int a,int b,float compliance,HashSet<ulong> edges)
        {
            if(a==b||Particles[a].group!=Particles[b].group||!edges.Add(Key(a,b)))return false;
            float length=Vector3.Distance(Particles[a].rest,Particles[b].rest)*scale;
            if(length<.0001f)return false;
            links.Add(new Link{a=a,b=b,rest=length,compliance=compliance});
            neighbours[a].Add(b);neighbours[b].Add(a);return true;
        }
        void Bend(int a,int b,int opposite,Dictionary<ulong,int> across)
        {
            var key=Key(a,b);
            if(across.TryGetValue(key,out var other))
            {
                if(other!=opposite&&Particles[other].group==Particles[opposite].group&&bendKeys.Add(Key(other,opposite)))
                    links.Add(new Link{a=other,b=opposite,rest=Vector3.Distance(Particles[other].rest,Particles[opposite].rest)*scale,compliance=.0015f});
            }
            else across.Add(key,opposite);
        }
        public void SetTargets(Matrix4x4[] drivers)
        {
            for(int i=0;i<Particles.Length;i++)
            {var p=Particles[i];p.target=drivers[p.group].MultiplyPoint3x4(p.rest);Particles[i]=p;}
        }
        public void Reset()
        {
            Release(0);Release(1);
            for(int i=0;i<Particles.Length;i++){var p=Particles[i];p.position=p.previous=p.target;Particles[i]=p;}
        }
        public bool Grab(int hand,Vector3 point,float reach)
        {
            float best=reach*reach;int chosen=-1;
            for(int i=0;i<Particles.Length;i++)
            {
                if(Particles[i].inverseMass<.12f||Grips[1-hand].particle==i)continue;
                float d=(Particles[i].position-point).sqrMagnitude;
                if(d<best){best=d;chosen=i;}
            }
            if(chosen<0)return false;
            Grips[hand]=new Grip{particle=chosen,offset=Particles[chosen].position-point,target=Particles[chosen].position};
            GrabStarts++;return true;
        }
        public void MoveGrip(int hand,Vector3 point)
        {var grip=Grips[hand];grip.target=point+grip.offset;Grips[hand]=grip;}
        public void Release(int hand){Grips[hand]=new Grip{particle=-1};}
        public void Step(float delta,List<Capsule> body,List<Capsule>[] hands,Vector3 wind)
        {
            int steps=Mathf.Clamp(Mathf.CeilToInt(delta*90),1,2);float dt=Mathf.Clamp(delta, .001f,.0222f)/steps;
            Contacts=0;MaximumOffset=0;
            for(int step=0;step<steps;step++)
            {
                for(int i=0;i<links.Count;i++){var link=links[i];link.lambda=0;links[i]=link;}
                for(int i=0;i<Particles.Length;i++)
                {
                    var p=Particles[i];
                    if(p.inverseMass==0){p.position=p.previous=p.target;Particles[i]=p;continue;}
                    var velocity=(p.position-p.previous)*Mathf.Exp(-3.5f*dt);
                    p.previous=p.position;
                    p.position+=velocity+(Vector3.down*9.81f+wind)*(dt*dt);
                    Particles[i]=p;
                }
                for(int iteration=0;iteration<4;iteration++)
                {
                    for(int i=0;i<links.Count;i++)
                    {
                        var link=links[i];ref var a=ref Particles[link.a];ref var b=ref Particles[link.b];
                        var difference=a.position-b.position;float length=difference.magnitude;
                        float sum=a.inverseMass+b.inverseMass;
                        if(length<1e-8f||sum<=0)continue;
                        float alpha=link.compliance/(dt*dt);
                        float dl=(-(length-link.rest)-alpha*link.lambda)/(sum+alpha);
                        var correction=difference*(dl/length);
                        a.position+=correction*a.inverseMass;b.position-=correction*b.inverseMass;
                        link.lambda+=dl;links[i]=link;
                    }
                    for(int i=0;i<Particles.Length;i++)
                    {
                        var p=Particles[i];if(p.inverseMass==0)continue;
                        var offset=p.position-p.target;
                        float allowed=p.travel;
                        if(offset.sqrMagnitude>allowed*allowed)p.position=p.target+Vector3.ClampMagnitude(offset,allowed);
                        foreach(var capsule in body)Project(ref p,capsule);
                        for(int h=0;h<2;h++)
                        {
                            bool heldNearby=Grips[h].particle>=0&&(p.position-Particles[Grips[h].particle].position).sqrMagnitude<.002f*scale*scale;
                            var capsules=hands[h];
                            if(!heldNearby&&capsules.Count>0&&(p.position-capsules[capsules.Count-1].a).sqrMagnitude<.24f*.24f)
                                foreach(var capsule in capsules)Project(ref p,capsule);
                        }
                        Particles[i]=p;
                    }
                    for(int h=0;h<2;h++)if(Grips[h].particle>=0)
                    {
                        int id=Grips[h].particle;var p=Particles[id];
                        // Soft positional attachment with a finite reach. Structural
                        // XPBD constraints spread traction instead of moving a bone.
                        var target=p.target+Vector3.ClampMagnitude(Grips[h].target-p.target,p.travel);
                        p.position=Vector3.Lerp(p.position,target,.82f);Particles[id]=p;
                    }
                }
                for(int i=0;i<Particles.Length;i++)
                {
                    var p=Particles[i];var velocity=Vector3.ClampMagnitude((p.position-p.previous)/dt,2.5f);
                    p.previous=p.position-velocity*dt;Particles[i]=p;
                    MaximumOffset=Mathf.Max(MaximumOffset,Vector3.Distance(p.position,p.target));
                }
            }
        }
        void Project(ref Particle p,Capsule capsule)
        {
            var axis=capsule.b-capsule.a;
            float t=axis.sqrMagnitude>1e-10f?Mathf.Clamp01(Vector3.Dot(p.position-capsule.a,axis)/axis.sqrMagnitude):0;
            var point=capsule.a+axis*t;var normal=p.position-point;float squared=normal.sqrMagnitude;
            if(squared>=capsule.radius*capsule.radius||squared<1e-14f)return;
            float distance=Mathf.Sqrt(squared);
            p.position=point+normal*(capsule.radius/distance);Contacts++;
        }
        public void WriteVertices(Matrix4x4[] drivers,Matrix4x4 worldToLocal,Vector3[] output)
        {
            for(int i=0;i<output.Length;i++)
            {
                var position=drivers[renderGroup[i]].MultiplyPoint3x4(renderRest[i]);
                for(int k=0;k<4;k++)
                {var p=Particles[influence[i,k]];position+=(p.position-p.target)*weights[i,k];}
                output[i]=worldToLocal.MultiplyPoint3x4(position);
            }
        }
    }
}
