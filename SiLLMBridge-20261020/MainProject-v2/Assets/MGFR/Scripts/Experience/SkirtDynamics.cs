using UnityEngine;
using MGFR.Character;

namespace MGFR.Experience
{
    [DefaultExecutionOrder(1400)]
    public sealed class SkirtDynamics : MonoBehaviour
    {
        const int Rows=12, Columns=16, Count=Rows*Columns;
        Transform[] bones=new Transform[Count];
        Vector3[] rest=new Vector3[Count],target=new Vector3[Count],points=new Vector3[Count],previous=new Vector3[Count];
        float[] vertical=new float[Count],horizontal=new float[Count];
        Transform anchor;
        Transform[] legs;
        ControllerHands hands;
        Vector3 lastAnchor;
        float lastScale;
        public bool Simulate=true;
        public float PeakDisplacement {get;private set;}
        public float LastMilliseconds {get;private set;}
        public int HandContacts {get;private set;}

        public void Bind(SiCharacterLoader loader,ControllerHands controllers)
        {
            hands=controllers;var rig=loader.Renderer.bones;anchor=rig[13];
            legs=new[]{rig[21],rig[22],rig[25],rig[26]};
            var a=loader.Data.bones[13].positionScaled;var origin=new Vector3(a[0],a[1],a[2]);
            for(int r=0;r<Rows;r++)for(int c=0;c<Columns;c++)
            {
                int k=r*Columns+c;
                int index=System.Array.FindIndex(loader.Data.bones,b=>b.name=="裙子_"+r+"_"+c);
                bones[k]=rig[index];var p=loader.Data.bones[index].positionScaled;
                rest[k]=new Vector3(p[0],p[1],p[2])-origin;
            }
            for(int r=0;r<Rows;r++)for(int c=0;c<Columns;c++)
            {
                int k=r*Columns+c;
                if(r>0)vertical[k]=Vector3.Distance(rest[k],rest[k-Columns]);
                horizontal[k]=Vector3.Distance(rest[k],rest[r*Columns+(c+1)%Columns]);
            }
            ResetSimulation();
        }
        public void ResetSimulation()
        {
            for(int k=0;k<Count;k++)points[k]=previous[k]=target[k]=anchor.TransformPoint(rest[k]);
            lastAnchor=anchor.position;lastScale=anchor.lossyScale.x;
        }
        void LateUpdate()=>Tick(Time.deltaTime,Time.time);
        public void Tick(float delta,float now)
        {
            var timer=System.Diagnostics.Stopwatch.StartNew();
            float scale=anchor.lossyScale.x;
            if(Vector3.Distance(anchor.position,lastAnchor)>.35f||Mathf.Abs(scale-lastScale)>.02f)ResetSimulation();
            lastAnchor=anchor.position;lastScale=scale;
            for(int k=0;k<Count;k++)target[k]=anchor.TransformPoint(rest[k]);
            float dt=Mathf.Min(delta,1f/30f)/2;
            HandContacts=0;
            for(int step=0;step<2;step++)
            {
                for(int k=0;k<Count;k++)
                {
                    if(k<Columns||!Simulate){points[k]=previous[k]=target[k];continue;}
                    float hem=(k/Columns)/(float)(Rows-1);
                    var wind=anchor.rotation*new Vector3(Mathf.Sin(now*1.1f+k%Columns*.22f)*.18f,0,
                        Mathf.Sin(now*.73f+k%Columns*.4f)*.12f)*scale*hem;
                    Vector3 velocity=(points[k]-previous[k])*Mathf.Exp(-7*dt);
                    var next=points[k]+velocity+((target[k]-points[k])*85+wind+Vector3.down*.08f*scale*hem)*dt*dt;
                    previous[k]=points[k];points[k]=next;
                }
                for(int iteration=0;iteration<5;iteration++)
                {
                    for(int r=1;r<Rows;r++)for(int c=0;c<Columns;c++)
                    {
                        int k=r*Columns+c;
                        Constrain(k-Columns,k,vertical[k]*scale,r==1?0:.5f);
                        Constrain(k,r*Columns+(c+1)%Columns,horizontal[k]*scale,.5f);
                        points[k]=target[k]+Vector3.ClampMagnitude(points[k]-target[k],.045f*scale*r/(Rows-1));
                        for(int l=0;l<4;l+=2)Capsule(k,legs[l].position,legs[l+1].position,.055f*scale);
                        foreach(var hand in hands.Hands)if(hand.Active)
                        {
                            Vector3 d=points[k]-hand.Position;float length=d.magnitude;
                            if(length<.065f*scale&&length>.0001f)
                            {points[k]=hand.Position+d/length*.065f*scale;HandContacts++;}
                        }
                    }
                }
            }
            PeakDisplacement=0;
            for(int k=0;k<Count;k++)
            {
                PeakDisplacement=Mathf.Max(PeakDisplacement,Vector3.Distance(target[k],points[k]));
                var rotation=anchor.rotation;
                if(k<Count-Columns)
                    rotation=Quaternion.FromToRotation(anchor.TransformVector(rest[k+Columns]-rest[k]),points[k+Columns]-points[k])*anchor.rotation;
                bones[k].SetPositionAndRotation(points[k],rotation);
            }
            timer.Stop();LastMilliseconds=(float)timer.Elapsed.TotalMilliseconds;
        }
        void Constrain(int a,int b,float length,float leftWeight)
        {
            var d=points[b]-points[a];float distance=d.magnitude;
            if(distance<.000001f)return;
            var correction=d*(1-length/distance);
            points[a]+=correction*leftWeight;points[b]-=correction*(1-leftWeight);
        }
        void Capsule(int k,Vector3 a,Vector3 b,float radius)
        {
            var ab=b-a;float t=Mathf.Clamp01(Vector3.Dot(points[k]-a,ab)/ab.sqrMagnitude);
            var center=a+ab*t;var d=points[k]-center;float n=d.magnitude;
            if(n<radius&&n>.00001f)points[k]=center+d*(radius/n);
        }
    }
}
