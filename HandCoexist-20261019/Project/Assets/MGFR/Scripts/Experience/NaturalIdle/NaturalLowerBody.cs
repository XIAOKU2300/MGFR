using UnityEngine;

namespace MGFR.Experience
{
    public struct LowerBodyPose
    {
        public Vector3 Hips, Pelvis, Left, Right;
        public float LeftPitch, RightPitch, LeftYaw, RightYaw;
        public int Action;
    }
    public sealed class NaturalLowerBody
    {
        sealed class Curve
        {
            readonly float[] values,slopes;
            static readonly float[] times={0,.08f,.16f,.26f,.36f,.46f,.58f,.66f,.76f,.86f,.93f,.97f,1};
            public Curve(params float[] input)
            {
                values=input;slopes=new float[input.Length];
                for(int i=1;i<input.Length-1;i++)
                {
                    float h0=times[i]-times[i-1],h1=times[i+1]-times[i];
                    float a=(input[i]-input[i-1])/h0,b=(input[i+1]-input[i])/h1;
                    if(a*b>0){float w0=2*h1+h0,w1=h1+2*h0;slopes[i]=(w0+w1)/(w0/a+w1/b);}
                }
            }
            public float At(float phase)
            {
                if(phase<=0||phase>=1)return 0;
                int i=0;while(i<values.Length-2&&phase>times[i+1])i++;
                float h=times[i+1]-times[i],u=(phase-times[i])/h,u2=u*u,u3=u2*u;
                return (2*u3-3*u2+1)*values[i]+(u3-2*u2+u)*h*slopes[i]+
                    (-2*u3+3*u2)*values[i+1]+(u3-u2)*h*slopes[i+1];
            }
        }
        static readonly Curve Weight=new Curve(0,.08f,.40f,.85f,1,1,1,1,.88f,.40f,.10f,.02f,0);
        static readonly Curve Heel=new Curve(0,0,.04f,.48f,.94f,1,.94f,.60f,.18f,.02f,0,0,0);
        static readonly Curve Lift=new Curve(0,0,.02f,.70f,1,0,0,.04f,1,.68f,.02f,0,0);
        static readonly Curve Reach=new Curve(0,0,0,.25f,.80f,1,1,1,.80f,.25f,0,0,0);
        static readonly Curve Flex=new Curve(0,.08f,.35f,.75f,1,.80f,.60f,.80f,1,.62f,.18f,.02f,0);
        static readonly Curve Ankle=new Curve(0,0,0,.45f,1,0,0,0,1,.40f,0,0,0);
        public const int AuthoredKeys=78,ActionCount=6;
        public LowerBodyPose Sample(float seconds,float strength=1)
        {
            // Six phrases, alternating support legs. Quiet gaps and different
            // durations prevent a metronomic marching loop. Every phrase returns
            // to the same footprint; room placement never changes.
            int slot=Mathf.FloorToInt(seconds/13f),action=((slot%6)+6)%6;
            float duration=action==0?8.5f:action==1?9.1f:action==2?8.8f:action==3?8.3f:action==4?9.5f:8.7f;
            float p=(seconds-slot*13-1.7f)/duration;
            bool left=action==0||action==2||action==4;float side=left?1:-1;
            float weight=Weight.At(p),heel=Heel.At(p),lift=Lift.At(p),reach=Reach.At(p);
            var pose=new LowerBodyPose{Action=action};
            pose.Hips=new Vector3(-side*.012f*weight,-.0015f-.0025f*Flex.At(p),-.0012f*weight)*strength;
            pose.Pelvis=new Vector3(.20f*Flex.At(p),-.35f*side*weight,.70f*side*weight)*strength;
            Vector3 offset=Vector3.zero;float pitch=0,yaw=0;
            switch(action)
            {
                case 0:case 3: // Toe remains on the ground; ankle pivots about it.
                    pitch=-6.5f*heel;break;
                case 1: // Right foot eases back, settles, then returns.
                    offset=new Vector3(-.009f*reach,.019f*lift,.025f*reach);
                    yaw=-2.3f*reach;pitch=2*Ankle.At(p);break;
                case 2:case 5: // Small forward toe placement, with a distinct swing arc.
                    offset=new Vector3(side*.006f*reach,.020f*lift,-.032f*reach);
                    pitch=2.5f*Ankle.At(p);break;
                case 4: // Unweight and adjust left foot, then recover the footprint.
                    offset=new Vector3(.023f*reach,.023f*lift,-.012f*reach);
                    yaw=2.8f*reach;pitch=2*Ankle.At(p);break;
            }
            if(left){pose.Left=offset*strength;pose.LeftPitch=pitch*strength;pose.LeftYaw=yaw*strength;}
            else {pose.Right=offset*strength;pose.RightPitch=pitch*strength;pose.RightYaw=yaw*strength;}
            return pose;
        }
    }
}
