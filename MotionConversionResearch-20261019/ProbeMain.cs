using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Numerics;
using System.Text.Json;
using Ruri.RipperHook.Humanoid;

// Math-only adapter. Input is an explicit per-clip scalar binding manifest.
public static class ProbeMain {
 public static void Main(string[] args) {
  if(args.Length!=4) throw new ArgumentException("avatar, channel manifest, scalar samples, NEW output");
  var rig=AvatarMuscleReferential.TryCreateFromDocument(File.ReadAllText(args[0])) ?? throw new Exception("Avatar invalid");
  var channels=JsonSerializer.Deserialize<Dictionary<string,int>>(File.ReadAllText(args[1]))!;
  var plan=rig.BindClip(channels);
  using var reader=new BinaryReader(File.OpenRead(args[2]));
  if(System.Text.Encoding.ASCII.GetString(reader.ReadBytes(8))!="ACLBAKE1" || reader.ReadByte()!=0)throw new Exception("sample header");
  reader.ReadUInt16(); int tracks=reader.ReadInt32(),frames=reader.ReadInt32(); float fps=reader.ReadSingle(),duration=reader.ReadSingle();
  if(channels.Values.Any(c=>c<0||c>=tracks))throw new Exception("channel overflow");
  var rows=new List<object>(); var frame=new float[tracks]; var quats=new Quaternion[AvatarMuscleReferential.SlotCount];var driven=new bool[quats.Length];
  static float[] Q(Quaternion q)=>new[]{q.X,q.Y,q.Z,q.W};
  static float[] V(Vector3 v)=>new[]{v.X,v.Y,v.Z};
  for(int f=0;f<frames;f++) {
   for(int c=0;c<tracks;c++)frame[c]=reader.ReadSingle();
   rig.BodyLocalQuats(frame,quats,driven);
   var b=rig.BodyTransform(frame,plan,quats,driven);
   if(b is null)throw new Exception("Missing root");
   quats[0]=b.Value.Rotation;driven[0]=true;
   rows.Add(new { rotations=rig.DrivenBones.Select(bone=>Q(quats[bone.Slot])).ToArray(), hips=V(b.Value.Position), motionT=V(b.Value.Motion.Position),motionQ=Q(b.Value.Motion.Rotation) });
  }
  using var output=new FileStream(args[3],FileMode.CreateNew);
  JsonSerializer.Serialize(output,new {fps,duration,frames,bones=rig.DrivenBones.Select(b=>new {b.Path,b.Slot}).ToArray(),samples=rows});
  Console.WriteLine($"solved {frames} frames, {rig.DrivenBones.Count} body bones");
 }
}
