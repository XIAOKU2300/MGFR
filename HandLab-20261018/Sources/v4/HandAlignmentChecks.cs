using System;
using UnityEditor;
using UnityEngine;

namespace MGFR.BareHands
{
    public static class HandAlignmentChecks
    {
        static void Equal(Vector3 a, Vector3 b, string message)
        {
            if (Vector3.Distance(a, b) > .00001f) throw new Exception(message + " " + a + " != " + b);
        }
        public static void Build()
        {
            var head = new Pose(new Vector3(1, 1.6f, -2), Quaternion.Euler(15, 65, 3));
            var wrist = new Vector3(1.25f, 1.2f, -1.4f);
            var raw = new Pose(wrist + new Vector3(.02f, .15f, .01f), Quaternion.Euler(25, 12, 20));
            var adjustment = new HandAlignment.Adjustment();
            Equal(HandAlignment.MapPose(raw, wrist, head, adjustment).position, raw.position, "identity");
            adjustment.offsetMetres = new Vector3(.005f, .02f, -.015f);
            var translated = HandAlignment.MapPose(raw, wrist, head, adjustment);
            Equal(translated.position - raw.position, head.rotation * adjustment.offsetMetres, "head-relative metric offset");
            adjustment.offsetMetres = Vector3.zero;
            adjustment.handScale = 1.2f;
            Equal(HandAlignment.MapPose(new Pose(wrist, raw.rotation), wrist, head, adjustment).position, wrist, "size must preserve wrist");
            Equal(HandAlignment.MapPose(raw, wrist, head, adjustment).position, wrist + (raw.position - wrist) * 1.2f, "size about wrist");
            adjustment.handScale = 1;
            adjustment.viewDegrees = new Vector3(.5f, -1, .5f);
            var turn = head.rotation * Quaternion.Euler(adjustment.viewDegrees) * Quaternion.Inverse(head.rotation);
            Equal(HandAlignment.MapPose(raw, wrist, head, adjustment).position, head.position + turn * (raw.position - head.position), "angular reprojection");
            var second = new Pose(raw.position + Vector3.right * .018f, raw.rotation);
            var a = HandAlignment.MapPose(raw, wrist, head, adjustment);
            var b = HandAlignment.MapPose(second, wrist, head, adjustment);
            if (Mathf.Abs(Vector3.Distance(a.position, b.position) - .018f) > .00001f) throw new Exception("rigid correction must preserve pinch distance");
            var profile = new HandAlignment.Profile(); profile.left = adjustment;
            var copy = JsonUtility.FromJson<HandAlignment.Profile>(JsonUtility.ToJson(profile));
            Equal(copy.left.viewDegrees, adjustment.viewDegrees, "profile roundtrip");
            Equal(copy.right.offsetMetres, Vector3.zero, "independent right hand");
            Debug.Log("[MGFR hand alignment checks] PASS identity, head-relative metric offset, wrist-fixed scale, angular reprojection, pinch distance, independent settings and JSON roundtrip.");
            HandsBuild.Build();
        }
    }
}
