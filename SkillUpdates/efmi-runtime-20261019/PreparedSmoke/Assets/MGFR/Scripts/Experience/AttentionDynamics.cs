using System;

namespace MGFR.Attention
{
    public enum AttentionMode { Listening, Speaking, Thinking }
    public enum FaceMood { Neutral, Warm, Thinking, Concerned, Surprised, Shy }
    public struct AttentionInput
    {
        public bool Tracked;
        public double Yaw,Pitch,Distance;
        public AttentionMode Mode;
    }
    public struct FaceWeights
    {
        public double SmileBrows,ConcernBrows,RaiseBrows,SmileCorners,FrownCorners,SoftEyes,WideEyes,Blush;
        public static FaceWeights Lerp(FaceWeights a,FaceWeights b,double t)=>new FaceWeights {
            SmileBrows=a.SmileBrows+(b.SmileBrows-a.SmileBrows)*t,ConcernBrows=a.ConcernBrows+(b.ConcernBrows-a.ConcernBrows)*t,
            RaiseBrows=a.RaiseBrows+(b.RaiseBrows-a.RaiseBrows)*t,SmileCorners=a.SmileCorners+(b.SmileCorners-a.SmileCorners)*t,
            FrownCorners=a.FrownCorners+(b.FrownCorners-a.FrownCorners)*t,SoftEyes=a.SoftEyes+(b.SoftEyes-a.SoftEyes)*t,
            WideEyes=a.WideEyes+(b.WideEyes-a.WideEyes)*t,Blush=a.Blush+(b.Blush-a.Blush)*t };
    }
    public struct AttentionOutput
    {
        public double HeadYaw,HeadPitch,HeadRoll,NeckYaw,NeckPitch;
        public double EyeOffsetYaw,EyeOffsetPitch,Blink;
        public bool HasTarget,LookingAway;
        public FaceWeights Expression;
    }
    public static class AttentionMath
    {
        public static bool Finite(double value)=>!double.IsNaN(value)&&!double.IsInfinity(value);
        public static double Clamp(double v,double low,double high)=>Math.Max(low,Math.Min(high,v));
        public static double Ease(double t){t=Clamp(t,0,1);return t*t*t*(t*(6*t-15)+10);}
    }
    public sealed class AngleMotor
    {
        public double Angle {get;private set;}
        public double Velocity {get;private set;}
        public void Reset(){Angle=Velocity=0;}
        public double Step(double target,double delta,double frequency,double speed,double acceleration)
        {
            if(!AttentionMath.Finite(target)||!AttentionMath.Finite(delta)||delta<=0)return Angle;
            delta=Math.Min(delta,.20);
            int steps=Math.Max(1,(int)Math.Ceiling(delta*240));double h=delta/steps;
            for(int i=0;i<steps;i++)
            {
                double error=target-Angle;
                double force=frequency*frequency*error-2*frequency*Velocity;
                force=AttentionMath.Clamp(force,-acceleration,acceleration);
                Velocity=AttentionMath.Clamp(Velocity+force*h,-speed,speed);
                double movement=Velocity*h;
                if(error*movement>0&&Math.Abs(movement)>Math.Abs(error)){Angle=target;Velocity=0;}
                else Angle+=movement;
            }
            return Angle;
        }
    }
    public sealed class AttentionDynamics
    {
        readonly AngleMotor yaw=new AngleMotor(),pitch=new AngleMotor(),roll=new AngleMotor();
        uint random;
        double lastNow=-1,lastValid=-100,targetYaw,targetPitch,anchorYaw,anchorPitch,headWaitUntil;
        double blinkStart=double.NegativeInfinity,nextBlink=2.8,lastBlink=-100;
        double nextBreak=5,breakUntil=-1,breakSide=1;
        FaceMood mood;
        double moodStarted=-100,moodHold=2.5;
        FaceWeights expression;
        public AttentionOutput Current {get;private set;}
        public AttentionDynamics(uint seed=19){random=seed==0?19:seed;nextBlink=2.8+Next()*2.4;nextBreak=4.8+Next()*2.2;}
        double Next(){unchecked{random=random*1664525u+1013904223u;return (random>>8)/16777216.0;}}
        static bool Positive(string text,string phrase)
        {
            int offset=0;
            while(offset<text.Length)
            {
                int hit=text.IndexOf(phrase,offset,StringComparison.Ordinal);
                if(hit<0)return false;offset=hit+phrase.Length;
                int opening=text.LastIndexOf('“',hit),closing=text.LastIndexOf('”',hit);
                if(opening>closing)continue;
                int start=Math.Max(0,hit-7);
                for(int i=hit-1;i>=start;i--)if("，,。.!！?？;；".IndexOf(text[i])>=0){start=i+1;break;}
                string prefix=text.Substring(start,hit-start);
                bool negated=false;
                foreach(string n in new[]{"不要","不用","别","没","不"})
                    if(prefix.IndexOf(n,StringComparison.Ordinal)>=0){negated=true;break;}
                if(!negated)return true;
            }
            return false;
        }
        public static FaceMood MatchMood(string text)
        {
            if(string.IsNullOrWhiteSpace(text)||text.Length>2000)return FaceMood.Neutral;
            if(Positive(text,"吓一跳")||Positive(text,"没想到")||Positive(text,"惊讶"))return FaceMood.Surprised;
            if(Positive(text,"害羞")||Positive(text,"不好意思")||Positive(text,"别夸")||Positive(text,"脸红")||
                Positive(text,"笨蛋")||Positive(text,"才没有")||Positive(text,"别乱说"))return FaceMood.Shy;
            if(text.Contains("不开心")||text.Contains("不高兴"))return FaceMood.Concerned;
            if(Positive(text,"难过")||Positive(text,"担心")||Positive(text,"别着急"))return FaceMood.Concerned;
            if(Positive(text,"想一想")||Positive(text,"让我想")||Positive(text,"不确定"))return FaceMood.Thinking;
            if(Positive(text,"谢谢")||Positive(text,"开心")||Positive(text,"你好")||Positive(text,"太好了")||Positive(text,"喜欢"))return FaceMood.Warm;
            return FaceMood.Neutral;
        }
        public void SetMood(FaceMood value,double now,double hold=2.5)
        {
            if(!AttentionMath.Finite(now)||now<0||!AttentionMath.Finite(hold))return;
            mood=value;moodStarted=now;moodHold=AttentionMath.Clamp(hold,.4,8);
        }
        public bool TriggerBlink(double now)
        {
            if(!AttentionMath.Finite(now)||now-lastBlink<.8)return false;
            blinkStart=lastBlink=now;return true;
        }
        static FaceWeights Preset(FaceMood value)
        {
            switch(value)
            {
                case FaceMood.Warm:return new FaceWeights{SmileBrows=.18,SmileCorners=.26,SoftEyes=.075};
                case FaceMood.Thinking:return new FaceWeights{ConcernBrows=.11,RaiseBrows=.06,SmileCorners=.025};
                case FaceMood.Concerned:return new FaceWeights{ConcernBrows=.26,FrownCorners=.09};
                case FaceMood.Surprised:return new FaceWeights{RaiseBrows=.25,WideEyes=.18};
                case FaceMood.Shy:return new FaceWeights{SmileBrows=.12,SmileCorners=.17,SoftEyes=.045,Blush=.52};
                default:return default;
            }
        }
        public AttentionOutput Step(AttentionInput input,double now,double delta)
        {
            if(!AttentionMath.Finite(now)||now<0||now<lastNow||!AttentionMath.Finite(delta)||delta<0)return Current;
            if(lastNow<0){nextBlink+=now;nextBreak+=now;}
            lastNow=now;
            bool valid=input.Tracked&&AttentionMath.Finite(input.Yaw)&&AttentionMath.Finite(input.Pitch)&&
                AttentionMath.Finite(input.Distance)&&input.Distance>=.12&&input.Distance<=10&&
                Math.Abs(input.Yaw)<=82&&Math.Abs(input.Pitch)<=60;
            bool retarget=false;
            if(valid)
            {
                lastValid=now;
                double newYaw=AttentionMath.Clamp(input.Yaw,-70,70),newPitch=AttentionMath.Clamp(input.Pitch,-40,40);
                retarget=Math.Abs(newYaw-anchorYaw)+Math.Abs(newPitch-anchorPitch)>7;
                if(retarget)
                {
                    anchorYaw=newYaw;anchorPitch=newPitch;headWaitUntil=now+.13;
                    if(Math.Abs(newYaw-targetYaw)>22&&now-lastBlink>1.5)TriggerBlink(now+.04);
                }
                targetYaw=newYaw;targetPitch=newPitch;
            }
            else if(now-lastValid>.20){targetYaw=targetPitch=0;}
            bool hasTarget=valid||now-lastValid<=.20;
            if(valid&&now>=nextBreak)
            {
                breakUntil=now+(input.Mode==AttentionMode.Listening?.28:.42);
                breakSide=Next()<.5?-1:1;
                nextBreak=now+4.5+Next()*2.8;
            }
            bool away=valid&&now<breakUntil;
            double offsetYaw=away?breakSide*4.0:0,offsetPitch=away?1.2:0;
            bool thinking=mood==FaceMood.Thinking&&now-moodStarted<moodHold+.4;
            if(thinking){offsetYaw+=3.3;offsetPitch+=1.8;}
            double desiredYaw=hasTarget?AttentionMath.Clamp(targetYaw*.55+offsetYaw*.18,-34,34):0;
            double desiredPitch=hasTarget?AttentionMath.Clamp(targetPitch*.38,-17,17):0;
            if(now<headWaitUntil&&hasTarget){desiredYaw=yaw.Angle;desiredPitch=pitch.Angle;}
            double y=yaw.Step(desiredYaw,delta,9,55,230),p=pitch.Step(desiredPitch,delta,9,40,180);
            double r=roll.Step(thinking?-2.1:0,delta,8,20,90);
            if(now>=nextBlink&&now-blinkStart>.18)TriggerBlink(now);
            double t=now-blinkStart,blink=0;
            if(t>=0&&t<.045)blink=AttentionMath.Ease(t/.045);
            else if(t>=.045&&t<.065)blink=1;
            else if(t>=.065&&t<.17)blink=1-AttentionMath.Ease((t-.065)/.105);
            if(t>=.17&&lastBlink==blinkStart&&nextBlink<=blinkStart+.2)nextBlink=now+2.8+Next()*3.7;
            // Schedule at initiation too, including an explicitly requested blink.
            if(t>=0&&t<.17&&nextBlink<=now+.2)nextBlink=blinkStart+.17+2.8+Next()*3.7;
            double age=now-moodStarted;
            double strength=age<0?0:age<.28?AttentionMath.Ease(age/.28):
                age<moodHold?1:1-AttentionMath.Ease((age-moodHold)/.9);
            var target=Preset(mood);
            double blend=1-Math.Exp(-Math.Max(0,delta)*12);
            expression=FaceWeights.Lerp(expression,FaceWeights.Lerp(default,target,strength),blend);
            Current=new AttentionOutput{HeadYaw=y*.75,NeckYaw=y*.25,HeadPitch=p*.82,NeckPitch=p*.18,HeadRoll=r,
                EyeOffsetYaw=offsetYaw,EyeOffsetPitch=offsetPitch,Blink=AttentionMath.Clamp(blink,0,1),
                HasTarget=hasTarget,LookingAway=away,Expression=expression};
            return Current;
        }
    }
}
