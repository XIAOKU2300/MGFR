"""Second candidate: blend submitted head gestures through the existing gaze owner."""
import prepare_candidate as build

build.FIELDS=build.FIELDS.replace('  float sampleNow;', '  Vector3 headOffset,headVelocity;Quaternion[] baseLocal;\n  float sampleNow;')
build.TICK=build.TICK.replace('   var baseLocal=new Quaternion[targets.Length];','   if(baseLocal==null)baseLocal=new Quaternion[targets.Length];')
start=build.TICK.index('   if(attention!=null&&chosen>=0)')
end=build.TICK.index('\n  }\n  static bool IsLower',start)
build.TICK=build.TICK[:start]+'''   Vector3 desiredHead=Vector3.zero;
   if(chosen>=0){int h=Array.FindIndex(rig.nodes,n=>n.name=="Bip001_Head");
    var rest=new Quaternion(rig.nodes[h].q[0],rig.nodes[h].q[1],rig.nodes[h].q[2],rig.nodes[h].q[3]);var q=faceTurn*(sourceLocal[h]*Quaternion.Inverse(rest))*Quaternion.Inverse(faceTurn);var e=q.eulerAngles;
    desiredHead=new Vector3(Mathf.Clamp(Mathf.DeltaAngle(0,e.x),-12,12),Mathf.Clamp(Mathf.DeltaAngle(0,e.y),-12,12),Mathf.Clamp(Mathf.DeltaAngle(0,e.z),-8,8))*fade;
   }
   headOffset=Vector3.SmoothDamp(headOffset,desiredHead,ref headVelocity,.14f,80f,dt);
   if(attention!=null&&(chosen>=0||headOffset.sqrMagnitude>.0001f))attention.SubmitHeadGesture(headOffset,Time.unscaledTime);
'''+build.TICK[end:]

if __name__=='__main__':build.main()
