using System;
using UnityEngine;

namespace MGFR.Experience
{
    // Seekable authored motion. No frame-count randomness, cumulative transforms,
    // shared Random state, or short looping source pose. Units: degrees/metres.
    public sealed class NaturalIdlePose
    {
        sealed class Track
        {
            readonly float[] times, values, slopes;
            public int Count => times.Length;
            public Track(float[] t, params float[] v)
            {
                if(t.Length!=v.Length)throw new ArgumentException("Mismatched idle keys");
                times=t;values=v;slopes=new float[t.Length];
                for(int i=1;i<t.Length-1;i++)
                {
                    float h0=t[i]-t[i-1],h1=t[i+1]-t[i];
                    float a=(v[i]-v[i-1])/h0,b=(v[i+1]-v[i])/h1;
                    if(a*b>0){float w0=2*h1+h0,w1=h1+2*h0;slopes[i]=(w0+w1)/(w0/a+w1/b);}
                }
            }
            public float At(float t)
            {
                if(t<=0)return values[0];if(t>=1)return values[values.Length-1];
                int i=0;while(i<times.Length-2&&t>times[i+1])i++;
                float h=times[i+1]-times[i],u=(t-times[i])/h,u2=u*u,u3=u2*u;
                return (2*u3-3*u2+1)*values[i]+(u3-2*u2+u)*h*slopes[i]+
                    (-2*u3+3*u2)*values[i+1]+(u3-u2)*h*slopes[i+1];
            }
        }
        static readonly float[] BreathTimes={0,.07f,.14f,.22f,.30f,.38f,.45f,.53f,.63f,.74f,.84f,.93f,1};
        // Short inhalation, rounded peak, longer release and a quiet pause.
        static readonly Track[] Breaths={
            new Track(BreathTimes,0,.07f,.25f,.53f,.82f,1,.97f,.81f,.51f,.23f,.06f,0,0),
            new Track(BreathTimes,0,.05f,.20f,.48f,.78f,.98f,1,.85f,.58f,.28f,.08f,.01f,0),
            new Track(BreathTimes,0,.09f,.30f,.60f,.86f,1,.94f,.75f,.45f,.19f,.04f,0,0)};
        static readonly float[] PhraseTimes={0,.06f,.13f,.22f,.31f,.40f,.50f,.60f,.71f,.81f,.89f,.95f,1};
        static Track T(params float[] v)=>new Track(PhraseTimes,v);
        // Separate tracks retain anticipation, settling and delayed recovery.
        static readonly Track Lean=T(0,-.04f,.02f,.30f,.66f,.94f,1,.94f,.73f,.39f,.12f,.02f,0);
        static readonly Track Turn=T(0,0,-.03f,.12f,.47f,.83f,1,.94f,.67f,.30f,.05f,0,0);
        static readonly Track Shoulder=T(0,-.08f,-.14f,.12f,.58f,.95f,1,.72f,.32f,.08f,-.02f,0,0);
        static readonly Track Elbow=T(0,0,-.04f,-.08f,.20f,.68f,1,.94f,.61f,.25f,.06f,0,0);
        static readonly Track Wrist=T(0,0,0,-.03f,-.08f,.31f,.82f,1,.77f,.37f,.09f,.01f,0);
        static readonly Track Finger=T(0,0,0,0,-.02f,.13f,.58f,1,.90f,.51f,.16f,.02f,0);
        static readonly Track HeadTurn=T(0,-.02f,.05f,.44f,.88f,1,.95f,.78f,.45f,.16f,.02f,0,0);
        static readonly Track HeadTilt=T(0,0,-.05f,.12f,.54f,.90f,1,.87f,.55f,.22f,.03f,0,0);
        static readonly Track Relax=T(0,.05f,.23f,.62f,1,.92f,.63f,.30f,.08f,-.03f,-.02f,0,0);
        public const int AuthoredKeys=156; // 3 breath tracks + 9 phrase tracks, each 13 keys.

        static float Hash(int n)
        {
            unchecked {uint x=(uint)n+0x9e3779b9u;x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;x^=x>>16;return (x&0xffffff)/16777215f;}
        }
        static float Smooth(float x)=>x*x*x*(x*(x*6-15)+10);
        static float Drift(float seconds,float span,int salt)
        {
            float t=seconds/span;int cell=Mathf.FloorToInt(t);
            return Mathf.Lerp(Hash(cell+salt),Hash(cell+salt+1),Smooth(t-cell))*2-1;
        }
        public float Breath(float seconds,float lag=0)
        {
            double t=seconds-lag;
            // Strictly monotonic phase warp: no hard reset when pace changes.
            double cycles=t/5.15+.065*Math.Sin(t*.173)+.026*Math.Sin(t*.071);
            int cycle=(int)Math.Floor(cycles);float phase=(float)(cycles-cycle);
            float depth=.86f+.22f*Hash(cycle+147);
            return Breaths[(int)(Hash(cycle+983)*2.999f)].At(phase)*depth;
        }
        void Phrase(float seconds,out float phase,out float side,out int kind,out float amplitude)
        {
            int slot=Mathf.FloorToInt(seconds/23f);
            float begin=slot*23+2+Hash(slot+239)*4;
            float duration=12+Hash(slot+773)*7;
            phase=(seconds-begin)/duration;
            if(phase<=0||phase>=1){phase=0;amplitude=0;}else amplitude=.65f+.35f*Hash(slot+533);
            side=Hash(slot+641)>.5f?1:-1;
            kind=(int)(Hash(slot+987)*3.999f);
        }
        public Vector3 Translation(int bone,float seconds)
        {
            float breath=Breath(seconds)-.44f;
            if(bone==5)return new Vector3(.006f*Drift(seconds,11.7f,91),.0009f*breath,.002f*Drift(seconds,13.1f,311));
            if(bone==14)return new Vector3(0,.00065f*breath,-.00065f*breath);
            if(bone==15)return new Vector3(0,.00125f*breath,-.00115f*breath);
            if(bone==29||bone==55)return new Vector3(0,.0008f*(Breath(seconds,.17f)-.44f),0);
            return Vector3.zero;
        }
        public Vector3 Angles(int bone,float seconds)
        {
            Phrase(seconds,out float phase,out float side,out int kind,out float amplitude);
            float b=Breath(seconds)-.44f;
            float lean=Lean.At(phase)*side*amplitude,turn=Turn.At(phase)*side*amplitude;
            float sway=Drift(seconds,11.7f,91),fore=Drift(seconds,13.1f,311);
            float release=kind==3?Relax.At(phase)*amplitude:0;
            switch(bone)
            {
                case 12:return new Vector3(.14f*fore,.25f*turn,-.32f*sway-.22f*lean);
                case 13:return new Vector3(-.48f*b+.22f*fore+.28f*release,.48f*turn,.34f*sway+.40f*lean);
                case 14:return new Vector3(-.68f*(Breath(seconds,.08f)-.44f)-.20f*release,.30f*turn,.22f*lean);
                case 15:return new Vector3(-.88f*(Breath(seconds,.15f)-.44f)-.35f*release,.32f*turn,-.12f*sway);
                case 29:case 55:
                    float sign=bone==29?1:-1;
                    return new Vector3(-.18f*b,0,sign*(.32f*(Breath(seconds,.22f)-.44f)-.65f*release));
                case 32:case 58:
                    float armSide=bone==32?1:-1;
                    float arm=(kind==0||kind==2)&&side==armSide?Shoulder.At(phase)*amplitude:0;
                    return new Vector3(.55f*(Breath(seconds,.27f)-.44f)+1.8f*arm,
                        armSide*(.28f*turn+.8f*arm),armSide*(.42f*b+1.8f*arm-.32f*release));
                case 35:case 61:
                    float elbowSide=bone==35?1:-1;
                    float elbow=(kind==0||kind==2)&&side==elbowSide?Elbow.At(phase)*amplitude:0;
                    return new Vector3(.38f*(Breath(seconds,.36f)-.44f)+3.1f*elbow,elbowSide*.6f*elbow,0);
                case 38:case 64:
                    float wristSide=bone==38?1:-1;
                    float wrist=side==wristSide?Wrist.At(phase)*amplitude:0;
                    return new Vector3(.36f*(Breath(seconds,.46f)-.44f)-1.5f*wrist,
                        wristSide*(1.9f*wrist+.35f*Drift(seconds,7.3f,43)),wristSide*(1.2f*wrist+.22f*b));
            }
            // Proximal/intermediate/distal phalanges trail the wrist by increasing
            // amounts. Four fingers are not driven as a single rigid paddle.
            if((bone>=43&&bone<=54)||(bone>=69&&bone<=80))
            {
                int local=(bone>=69?bone-69:bone-43),finger=local/3,joint=local%3;
                float fingerSide=bone>=69?-1:1;
                float curl=Finger.At(Mathf.Clamp01(phase-finger*.008f-joint*.006f))*amplitude;
                float small=(Breath(seconds,.52f+finger*.025f)-.44f)*.22f;
                return new Vector3(0,0,fingerSide*(small+curl*(joint==0?1.8f:1.1f)));
            }
            return Vector3.zero;
        }
        public Vector3 Head(float seconds)
        {
            Phrase(seconds,out float p,out float side,out int kind,out float amplitude);
            return new Vector3(.40f*(Breath(seconds,.28f)-.44f)+.18f*Drift(seconds,10.3f,131),
                (kind==1?2.2f*HeadTurn.At(p)*side*amplitude:0)+.35f*Drift(seconds,15.7f,107),
                .32f*Drift(seconds,12.3f,337)+.70f*HeadTilt.At(p)*side*amplitude);
        }
        public Vector3 Air(float seconds,float depth=0)
        {
            // Coherent low-energy air. The hair/cloth solver supplies the lag;
            // forcing does not overwrite bones or grip ownership.
            float b=Breath(seconds,.22f+depth*.25f)-.44f;
            return new Vector3(.055f*Drift(seconds,6.7f,193)+.035f*b,
                .022f*b,.045f*Drift(seconds,8.3f,719)+.025f*b);
        }
    }
}
