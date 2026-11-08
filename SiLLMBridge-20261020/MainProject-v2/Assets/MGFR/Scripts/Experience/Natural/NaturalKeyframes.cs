using System;
using MGFR.SpeechMotion;

namespace MGFR.SpeechMotion.Natural
{
    public readonly struct PoseKey
    {
        public readonly double Time;
        public readonly Angles Rotation;
        public PoseKey(double time, double x = 0, double y = 0, double z = 0)
        { Time = time; Rotation = new Angles(x, y, z); }
    }

    // Authored key poses with shape-preserving cubic Hermite interpolation.
    // Endpoints stop at rest; intermediate motion keys retain continuous velocity.
    public sealed class JointKeyTrack
    {
        readonly PoseKey[] keys;
        readonly Angles[] slopes;
        public Joint Joint { get; }
        public int KeyCount => keys.Length;
        public PoseKey GetKey(int index) => keys[index];

        public JointKeyTrack(Joint joint, params PoseKey[] input)
        {
            if (joint < 0 || joint >= Joint.Count || input == null || input.Length < 2)
                throw new ArgumentException("A valid joint and at least two keys are required.");
            Joint = joint;
            keys = (PoseKey[])input.Clone();
            if (keys[0].Time != 0 || keys[keys.Length - 1].Time != 1)
                throw new ArgumentException("Tracks must span normalized time 0..1.");
            for (int i = 0; i < keys.Length; i++)
            {
                var k = keys[i];
                if (!MotionContract.Finite(k.Time) || !Finite(k.Rotation) ||
                    (i > 0 && k.Time <= keys[i - 1].Time))
                    throw new ArgumentException("Keys must be finite and strictly ordered.");
            }
            if (Magnitude(keys[0].Rotation) > 0 || Magnitude(keys[keys.Length - 1].Rotation) > 0)
                throw new ArgumentException("A conversational gesture must start and end at rest.");
            slopes = new Angles[keys.Length];
            for (int i = 1; i < keys.Length - 1; i++)
            {
                double before = keys[i].Time - keys[i - 1].Time;
                double after = keys[i + 1].Time - keys[i].Time;
                slopes[i] = new Angles(
                    Tangent(keys[i-1].Rotation.X, keys[i].Rotation.X, keys[i+1].Rotation.X, before, after),
                    Tangent(keys[i-1].Rotation.Y, keys[i].Rotation.Y, keys[i+1].Rotation.Y, before, after),
                    Tangent(keys[i-1].Rotation.Z, keys[i].Rotation.Z, keys[i+1].Rotation.Z, before, after));
            }
        }
        static bool Finite(Angles a) => MotionContract.Finite(a.X) && MotionContract.Finite(a.Y) && MotionContract.Finite(a.Z);
        static double Magnitude(Angles a) => Math.Abs(a.X) + Math.Abs(a.Y) + Math.Abs(a.Z);
        static double Tangent(double previous, double current, double next, double before, double after)
        {
            double left = (current - previous) / before, right = (next - current) / after;
            if (left * right <= 0) return 0;
            double w1 = 2 * after + before, w2 = after + 2 * before;
            return (w1 + w2) / (w1 / left + w2 / right);
        }
        public Angles Sample(double phase)
        {
            if (!MotionContract.Finite(phase) || phase <= 0 || phase >= 1) return default;
            int i = 0;
            while (i + 1 < keys.Length - 1 && phase > keys[i + 1].Time) i++;
            double width = keys[i+1].Time - keys[i].Time;
            double t = (phase - keys[i].Time) / width, t2 = t*t, t3 = t2*t;
            double h00 = 2*t3 - 3*t2 + 1, h10 = t3 - 2*t2 + t;
            double h01 = -2*t3 + 3*t2, h11 = t3 - t2;
            var a = keys[i].Rotation; var b = keys[i+1].Rotation;
            var ma = slopes[i]; var mb = slopes[i+1];
            return new Angles(h00*a.X + h10*width*ma.X + h01*b.X + h11*width*mb.X,
                h00*a.Y + h10*width*ma.Y + h01*b.Y + h11*width*mb.Y,
                h00*a.Z + h10*width*ma.Z + h01*b.Z + h11*width*mb.Z);
        }
    }

    public sealed class AuthoredGestureClip
    {
        readonly JointKeyTrack[] tracks;
        public Gesture Kind { get; }
        public int Variant { get; }
        public double Duration { get; }
        public int TrackCount => tracks.Length;
        public JointKeyTrack GetTrack(int index) => tracks[index];
        internal AuthoredGestureClip(Gesture kind, int variant, double duration, params JointKeyTrack[] input)
        { Kind = kind; Variant = variant; Duration = duration; tracks = input; }

        public void Add(double phase, double strength, bool mirror, MotionPose pose)
        {
            if (phase <= 0 || phase >= 1 || strength <= 0 || !MotionContract.Finite(phase) ||
                !MotionContract.Finite(strength)) return;
            foreach (var track in tracks)
            {
                Joint joint = mirror ? Mirrored(track.Joint) : track.Joint;
                Angles a = track.Sample(phase);
                // Rotation is an axial vector: reflection in the sagittal plane
                // preserves pitch and reverses yaw/roll.
                if (mirror) a = new Angles(a.X, -a.Y, -a.Z);
                pose[joint] = pose[joint] + new Angles(a.X*strength, a.Y*strength, a.Z*strength);
            }
            pose.ActiveGestures++;
        }
        static Joint Mirrored(Joint joint)
        {
            switch (joint)
            {
                case Joint.LeftArm: return Joint.RightArm;
                case Joint.RightArm: return Joint.LeftArm;
                case Joint.LeftElbow: return Joint.RightElbow;
                case Joint.RightElbow: return Joint.LeftElbow;
                case Joint.LeftWrist: return Joint.RightWrist;
                case Joint.RightWrist: return Joint.LeftWrist;
                default: return joint;
            }
        }
    }

    public static class NaturalGestureLibrary
    {
        static readonly AuthoredGestureClip[,] clips = Build();
        public const int VariantCount = 3;
        public static AuthoredGestureClip Get(Gesture kind, int variant)
        {
            if ((int)kind < 0 || (int)kind > (int)Gesture.PointRight || variant < 0 || variant >= VariantCount)
                throw new ArgumentOutOfRangeException();
            return clips[(int)kind, variant];
        }
        static JointKeyTrack Track(Joint j, params PoseKey[] keys) => new JointKeyTrack(j, keys);
        static PoseKey K(double t, double x=0, double y=0, double z=0) => new PoseKey(t,x,y,z);
        static AuthoredGestureClip[,] Build()
        {
            var result = new AuthoredGestureClip[7, VariantCount];
            for (int v=0; v<VariantCount; v++)
            {
                double side = v==1 ? -1 : 1;
                // Head nod: tiny anticipation, one clear downward stroke, soft recovery.
                result[(int)Gesture.Nod,v] = new AuthoredGestureClip(Gesture.Nod,v,v==2?1.02:.92,
                    Track(Joint.Head,K(0),K(.12,.65),K(.33,-(v==1?5.6:7.2),0,.35*side),
                        K(.42,-6.0),K(.70,.55),K(.86,.12),K(1)),
                    Track(Joint.Chest,K(0),K(.21),K(.43,-.65),K(.73,-.22),K(1)));
                // Shake: one left/right phrase with a smaller return, not a periodic oscillator.
                result[(int)Gesture.ShakeHead,v] = new AuthoredGestureClip(Gesture.ShakeHead,v,1.28+v*.06,
                    Track(Joint.Head,K(0),K(.10,-.2,1.0*side),K(.29,-.5,-7.8*side,.6),
                        K(.57,-.4,5.2*side,.2),K(.79,-.15,-1.1*side),K(1)));
                result[(int)Gesture.TiltHead,v] = new AuthoredGestureClip(Gesture.TiltHead,v,1.85+v*.08,
                    Track(Joint.Head,K(0),K(.15),K(.39,-.65,1.1*side,4.4*side),
                        K(.65,-.45,.8*side,4.1*side),K(.85,-.1,.2*side,1.7*side),K(1)));

                double raised = v==1 ? 49 : v==2 ? 58 : 54;
                // Wave: shoulder prepares first, elbow follows, wrist arrives last.
                // Positive elbow pitch bends toward the viewer in the arms-down demo rig.
                result[(int)Gesture.Wave,v] = new AuthoredGestureClip(Gesture.Wave,v,2.12+v*.08,
                    Track(Joint.RightArm,K(0),K(.065,-1,0,-1.4),K(.24,8,-65,raised),
                        K(.38,10,-82,raised+2),K(.64,9,-77,raised),K(.83,5,-30,27),K(1)),
                    Track(Joint.RightElbow,K(0),K(.12),K(.30,128),K(.40,142),K(.65,132),
                        K(.83,75),K(.96,1),K(1)),
                    Track(Joint.RightWrist,K(0),K(.27),K(.39,0,v==1?42:34,14),
                        K(.55,0,v==1?25:21,-9),K(.70,0,28,v==2?7:4),
                        K(.82,0,0,-1),K(.96),K(1)),
                    Track(Joint.Head,K(0),K(.16,-.4,-1.5,1.8*side),K(.58,-.3,-1,1.2*side),K(.85),K(1)),
                    Track(Joint.Chest,K(0),K(.22,-.4,-.4,.7),K(.62,-.3,-.2,.65),K(.87,-.1,0,.2),K(1)));
                // Explain: one open hand, moderate reach, elbow/wrist settle at different times.
                result[(int)Gesture.OpenPalm,v] = new AuthoredGestureClip(Gesture.OpenPalm,v,2.30+v*.10,
                    Track(Joint.RightArm,K(0),K(.08,-.6,0,-.8),K(.27,20,-4,32+v*3),
                        K(.51,22,-5,36+v*3),K(.68,20,-3,32),K(.86,8,-1,15),K(1)),
                    Track(Joint.RightElbow,K(0),K(.10),K(.30,60),K(.53,67),K(.70,59),K(.87,25),K(1)),
                    Track(Joint.RightWrist,K(0),K(.18),K(.37,-4,18,-12),K(.56,-3,22,-10),
                        K(.73,-2,15,-8),K(.91),K(1)),
                    Track(Joint.Chest,K(0),K(.26,-.3,-.6,.55),K(.58,-.4,-.8,.65),K(.85,-.1,-.2,.1),K(1)),
                    Track(Joint.Head,K(0),K(.18,-.5,.6,-.4),K(.58,-.7,.8,-.5),K(.88),K(1)));
                foreach (Gesture kind in new[]{Gesture.PointLeft,Gesture.PointRight})
                    result[(int)kind,v] = new AuthoredGestureClip(kind,v,2.04+v*.08,
                        // Base track points right. The left version is reflected when sampled.
                        Track(Joint.Head,K(0),K(.14,-.5,-7.0,-.6),K(.35,-.8,-9.5,-.4),K(.61,-.5,-7),
                            K(.84,-.1,-1.5),K(1)),
                        Track(Joint.RightArm,K(0),K(.12),K(.34,7,-4,68+v*3),
                            K(.58,8,-5,71+v*3),K(.75,6,-3,58),K(.91,2,-1,14),K(1)),
                        Track(Joint.RightElbow,K(0),K(.15),K(.34,24),K(.48,13),K(.65,15),K(.82,20),K(1)),
                        Track(Joint.RightWrist,K(0),K(.25),K(.43,0,3,5),K(.65,0,2,4),K(.87),K(1)),
                        Track(Joint.Chest,K(0),K(.23,-.2,-1.2,.45),K(.60,-.2,-1.5,.6),K(.89),K(1)));
            }
            return result;
        }

        public static void Limit(MotionPose pose)
        {
            for (int i=0; i<(int)Joint.Count; i++)
            {
                Joint j=(Joint)i; Angles a=pose[j];
                double limit=j==Joint.Head?12:j==Joint.Chest?3:
                    j==Joint.LeftWrist||j==Joint.RightWrist?22:
                    j==Joint.LeftElbow||j==Joint.RightElbow?135:85;
                pose[j]=new Angles(MotionContract.Clamp(a.X,-limit,limit),
                    MotionContract.Clamp(a.Y,-limit,limit),MotionContract.Clamp(a.Z,-limit,limit));
            }
        }
    }
}
