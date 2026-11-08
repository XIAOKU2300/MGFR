using System;

namespace MGFR.SpeechMotion
{
    public enum Joint { Head, Chest, LeftArm, LeftElbow, LeftWrist, RightArm, RightElbow, RightWrist, Count }
    public enum Gesture { Nod, ShakeHead, TiltHead, Wave, OpenPalm, PointLeft, PointRight }

    [Serializable]
    public sealed class MotionCue
    {
        public int version = 1;
        public string cueId;
        public string sessionId;
        public int round;
        public int sentenceIndex;
        public string gesture;
        public string hand = "right";
        public double startSeconds;
        public double durationSeconds = 2;
        public double strength = .65;
        public int repeats = 2;
        public int priority;
    }

    public sealed class ValidatedCue
    {
        public string Id { get; internal set; }
        public string Session { get; internal set; }
        public int Round { get; internal set; }
        public int Sentence { get; internal set; }
        public Gesture Gesture { get; internal set; }
        public bool LeftHand { get; internal set; }
        public double Start { get; internal set; }
        public double Duration { get; internal set; }
        public double Strength { get; internal set; }
        public int Repeats { get; internal set; }
        public int Priority { get; internal set; }
        public bool UsesHead => Gesture == Gesture.Nod || Gesture == Gesture.ShakeHead || Gesture == Gesture.TiltHead;
    }

    public struct Angles
    {
        public double X, Y, Z;
        public Angles(double x, double y, double z) { X = x; Y = y; Z = z; }
        public static Angles operator +(Angles a, Angles b) => new Angles(a.X+b.X, a.Y+b.Y, a.Z+b.Z);
    }

    public sealed class MotionPose
    {
        readonly Angles[] values = new Angles[(int)Joint.Count];
        public int ActiveGestures { get; internal set; }
        public Angles this[Joint joint] { get => values[(int)joint]; set => values[(int)joint] = value; }
        public void Clear() { Array.Clear(values, 0, values.Length); ActiveGestures = 0; }
        public bool IsNeutral
        {
            get { foreach (var a in values) if (Math.Abs(a.X)+Math.Abs(a.Y)+Math.Abs(a.Z) > .00001) return false; return true; }
        }
    }

    public static class MotionContract
    {
        public static bool Finite(double x) => !double.IsNaN(x) && !double.IsInfinity(x);
        public static double Clamp(double x, double min, double max) => Math.Max(min, Math.Min(max, x));
        public static bool TryValidate(MotionCue cue, out ValidatedCue result, out string error)
        {
            result = null;
            error = "";
            if (cue == null) { error = "cue is null"; return false; }
            if (cue.version != 1) { error = "unsupported motion version"; return false; }
            if (string.IsNullOrWhiteSpace(cue.cueId) || cue.cueId.Length > 128 ||
                string.IsNullOrWhiteSpace(cue.sessionId) || cue.sessionId.Length > 128)
            { error = "sessionId and cueId must be bounded nonempty strings"; return false; }
            if (cue.round < 1 || cue.sentenceIndex < 0) { error = "invalid round or sentence"; return false; }
            if (!Finite(cue.startSeconds) || cue.startSeconds < 0 || cue.startSeconds > 30 ||
                !Finite(cue.durationSeconds) || cue.durationSeconds <= 0 || !Finite(cue.strength))
            { error = "invalid timing or strength"; return false; }
            Gesture kind;
            switch (cue.gesture)
            {
                case "nod": kind = Gesture.Nod; break;
                case "shake_head": kind = Gesture.ShakeHead; break;
                case "tilt_head": kind = Gesture.TiltHead; break;
                case "wave": kind = Gesture.Wave; break;
                case "open_palm": kind = Gesture.OpenPalm; break;
                case "point_left": kind = Gesture.PointLeft; break;
                case "point_right": kind = Gesture.PointRight; break;
                default: error = "gesture is not allowlisted"; return false;
            }
            if (cue.hand != "left" && cue.hand != "right") { error = "hand must be left or right"; return false; }
            result = new ValidatedCue {
                Id = cue.cueId, Session = cue.sessionId, Round = cue.round, Sentence = cue.sentenceIndex,
                Gesture = kind, LeftHand = cue.hand == "left", Start = cue.startSeconds,
                Duration = Clamp(cue.durationSeconds, .4, 6), Strength = Clamp(cue.strength, 0, 1),
                Repeats = Math.Max(1, Math.Min(4, cue.repeats)), Priority = Math.Max(0, Math.Min(10, cue.priority))
            };
            return true;
        }
    }
}
