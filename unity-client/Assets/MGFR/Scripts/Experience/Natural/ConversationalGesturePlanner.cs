using System;
using System.Collections.Generic;

namespace MGFR.SpeechMotion.Natural
{
    public sealed class NaturalGestureCue
    {
        public Gesture Kind { get; }
        public int Variant { get; }
        public bool LeftHand { get; }
        public double Start { get; }
        public double Duration { get; }
        public double Strength { get; }
        public int KeywordIndex { get; }
        public bool GreetingFallback { get; }
        public bool UsesHead => Kind==Gesture.Nod || Kind==Gesture.ShakeHead || Kind==Gesture.TiltHead;
        internal NaturalGestureCue(Gesture kind,int variant,bool left,double start,double duration,
            double strength,int keywordIndex,bool greetingFallback)
        { Kind=kind; Variant=variant; LeftHand=left; Start=start; Duration=duration; Strength=strength;
            KeywordIndex=keywordIndex; GreetingFallback=greetingFallback; }
    }

    public sealed class NaturalSentencePlan
    {
        readonly NaturalGestureCue[] cues;
        public int Count => cues.Length;
        public NaturalGestureCue this[int index] => cues[index];
        internal NaturalSentencePlan(params NaturalGestureCue[] input) { cues=input; }
    }

    /// <summary>
    /// Bounded keyword rules, NOT general language understanding.
    /// Plan at actual sentence playback, not when a future buffered reply arrives.
    /// Commit history only when the gesture really begins; cancelled plans leave no history.
    /// </summary>
    public sealed class ConversationalGesturePlanner
    {
        readonly uint seed;
        readonly double[] lastStarted=new double[7];
        readonly int[] lastVariant=new int[7];
        double lastArm=double.NegativeInfinity,lastHead=double.NegativeInfinity;
        double lastGreetingFallback=double.NegativeInfinity;
        Gesture lastArmKind=Gesture.Wave,lastHeadKind=Gesture.Nod;
        bool hasArm,hasHead;
        static readonly string[] Negations={"不要","不用","不必","无需","禁止","别","不许","没让","没有让","不想","不是要","不是让","不"};
        static readonly NaturalSentencePlan Empty=new NaturalSentencePlan();
        public ConversationalGesturePlanner(string localSessionSeed)
        {
            seed=Hash(localSessionSeed ?? "");
            for(int i=0;i<7;i++) {lastStarted[i]=double.NegativeInfinity;lastVariant[i]=-1;}
        }
        static uint Hash(string text)
        {
            unchecked { uint value=2166136261; foreach(char c in text) {value^=c;value*=16777619;} return value; }
        }
        static bool Boundary(char c) => "，,。.!！?？;；\n".IndexOf(c)>=0;
        static bool Quoted(string text,int end)
        {
            bool chinese=false,ascii=false;
            for(int i=0;i<end;i++)
            {
                char c=text[i];
                if(c=='“'||c=='「'||c=='『') chinese=true;
                else if(c=='”'||c=='」'||c=='』') chinese=false;
                else if(c=='"') ascii=!ascii;
            }
            return chinese||ascii;
        }
        static int Find(string text,params string[] phrases)
        {
            int best=-1;
            foreach(string phrase in phrases)
            {
                int offset=0;
                while(offset<text.Length)
                {
                    int hit=text.IndexOf(phrase,offset,StringComparison.Ordinal);
                    if(hit<0) break;
                    offset=hit+phrase.Length;
                    if(Quoted(text,hit)) continue;
                    int start=Math.Max(0,hit-7);
                    for(int i=hit-1;i>=start;i--) if(Boundary(text[i])) {start=i+1;break;}
                    string prefix=text.Substring(start,hit-start);
                    bool negated=false;
                    foreach(string negation in Negations)
                        if(prefix.IndexOf(negation,StringComparison.Ordinal)>=0) {negated=true;break;}
                    if(negated) continue;
                    string tail=text.Substring(hit+phrase.Length,Math.Min(5,text.Length-hit-phrase.Length));
                    if(tail.StartsWith("这个词",StringComparison.Ordinal)||tail.StartsWith("这个动作",StringComparison.Ordinal)||
                        tail.StartsWith("是什么意思",StringComparison.Ordinal)) continue;
                    if(phrase=="你好"&&tail.Length>0&&"像漂厉可棒聪".IndexOf(tail[0])>=0) continue;
                    if(best<0||hit<best) best=hit;
                    break;
                }
            }
            return best;
        }
        static double EstimateKeywordTime(string text,int index)
        {
            double seconds=0;
            for(int i=0;i<index;i++)
            {
                char c=text[i];
                if(char.IsWhiteSpace(c)) seconds+=.025;
                else if("，,、".IndexOf(c)>=0) seconds+=.15;
                else if("。.!！?？;；".IndexOf(c)>=0) seconds+=.25;
                else seconds+=(c<128?.075:.155);
            }
            // Sentence-level approximation until real word timestamps exist.
            return Math.Max(.08,Math.Min(25,seconds-.08));
        }
        bool Available(Gesture kind,double now,bool explicitAction)
        {
            bool head=kind==Gesture.Nod||kind==Gesture.ShakeHead||kind==Gesture.TiltHead;
            if(now-(head?lastHead:lastArm)<(explicitAction?1.8:head?2.5:4.5)) return false;
            double cooldown=kind==Gesture.Wave?20:kind==Gesture.Nod?4.5:6;
            if(explicitAction) cooldown=2.6;
            if(now-lastStarted[(int)kind]<cooldown) return false;
            if(!explicitAction&&((head&&hasHead&&lastHeadKind==kind)||(!head&&hasArm&&lastArmKind==kind))&&
                now-lastStarted[(int)kind]<(head?9:12)) return false;
            return true;
        }
        NaturalGestureCue Make(Gesture kind,string text,int sentence,int hit,bool left,double userScale,bool fallback=false)
        {
            uint hash=Hash(text)^seed^unchecked((uint)sentence*2654435761u)^unchecked((uint)kind*2246822519u);
            int variant=(int)(hash%3);
            if(variant==lastVariant[(int)kind]) variant=(variant+1)%3;
            double variation=((hash>>8)%1001)/1000.0;
            double strength=(kind==Gesture.Nod?.68:kind==Gesture.ShakeHead?.64:.80)*(.91+.18*variation);
            if(text.IndexOf("轻轻",StringComparison.Ordinal)>=0||text.IndexOf("小声",StringComparison.Ordinal)>=0) strength*=.72;
            if(text.IndexOf('！')>=0||text.IndexOf('!')>=0) strength*=1.06;
            if(fallback) strength*=.52;
            strength=MotionContract.Clamp(strength*userScale,.18,1);
            double duration=NaturalGestureLibrary.Get(kind,variant).Duration*(.94+.12*(1-variation));
            return new NaturalGestureCue(kind,variant,left,EstimateKeywordTime(text,hit),duration,strength,hit,fallback);
        }

        public NaturalSentencePlan Plan(string text,int sentenceIndex,double performanceNow,double intensity=1)
        {
            if(string.IsNullOrWhiteSpace(text)||text.Length>2000||sentenceIndex<0||
                !MotionContract.Finite(performanceNow)||performanceNow<0||!MotionContract.Finite(intensity)) return Empty;
            intensity=MotionContract.Clamp(intensity,.25,1.2);
            var cues=new List<NaturalGestureCue>(2);
            bool left=text.IndexOf("左手",StringComparison.Ordinal)>=0;
            Gesture arm=Gesture.Wave; int armHit=-1; bool explicitArm=false;
            int hit=Find(text,"指向左","看左边","左边那个");
            if(hit>=0) {arm=Gesture.PointLeft;armHit=hit;explicitArm=true;}
            else if((hit=Find(text,"指向右","看右边","右边那个"))>=0) {arm=Gesture.PointRight;armHit=hit;explicitArm=true;}
            else if((hit=Find(text,"挥手","挥挥手","招手"))>=0) {arm=Gesture.Wave;armHit=hit;explicitArm=true;}
            else if((hit=Find(text,"摊手","给你看看","让我解释","举个例子","比如说"))>=0)
            {arm=Gesture.OpenPalm;armHit=hit;explicitArm=text.IndexOf("摊手",StringComparison.Ordinal)>=0;}
            int greeting=Find(text,"你好","回来啦","再见","拜拜");
            if(armHit<0&&greeting>=0) {arm=Gesture.Wave;armHit=greeting;}
            if(armHit>=0&&Available(arm,performanceNow,explicitArm))
                cues.Add(Make(arm,text,sentenceIndex,armHit,left,intensity));

            Gesture head=Gesture.Nod; int headHit=-1; bool explicitHead=false;
            if((hit=Find(text,"摇头","不同意","不太合适","不是这样","不是的","不对"))>=0)
            {head=Gesture.ShakeHead;headHit=hit;explicitHead=text.IndexOf("摇头",StringComparison.Ordinal)>=0;}
            else if((hit=Find(text,"点头","没错","是的","好的","当然可以","太好了"))>=0)
            {head=Gesture.Nod;headHit=hit;explicitHead=text.IndexOf("点头",StringComparison.Ordinal)>=0;}
            else if((hit=Find(text,"想一想","想想","让我想","歪头","不确定"))>=0)
            {head=Gesture.TiltHead;headHit=hit;explicitHead=text.IndexOf("歪头",StringComparison.Ordinal)>=0;}
            bool fallback=false;
            if(headHit<0&&greeting>=0&&cues.Count==0&&performanceNow-lastGreetingFallback>=12)
            {head=Gesture.Nod;headHit=greeting;fallback=true;}
            if(headHit>=0&&Available(head,performanceNow,explicitHead))
                cues.Add(Make(head,text,sentenceIndex,headHit,false,intensity,fallback));
            // Head acknowledges first; the hand starts slightly later.
            if(cues.Count==2&&Math.Abs(cues[0].Start-cues[1].Start)<.22)
            {
                var a=cues[0];
                cues[0]=new NaturalGestureCue(a.Kind,a.Variant,a.LeftHand,a.Start+.16,a.Duration,a.Strength,a.KeywordIndex,false);
            }
            return new NaturalSentencePlan(cues.ToArray());
        }
        public bool Commit(NaturalGestureCue cue,double performanceNow)
        {
            if(cue==null||!MotionContract.Finite(performanceNow)||performanceNow<0||
                performanceNow<lastStarted[(int)cue.Kind]) return false;
            lastStarted[(int)cue.Kind]=performanceNow;
            lastVariant[(int)cue.Kind]=cue.Variant;
            if(cue.UsesHead) {lastHead=performanceNow;lastHeadKind=cue.Kind;hasHead=true;}
            else {lastArm=performanceNow;lastArmKind=cue.Kind;hasArm=true;}
            if(cue.GreetingFallback) lastGreetingFallback=performanceNow;
            return true;
        }
    }
}
