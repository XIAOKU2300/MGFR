"""Smooth arm goals in collision-constrained space before solving the arm chains."""
import prepare_release
import prepare_candidate as build

ARM = '''  void ApplyNativeArm(ArmBinding arm,float weight,float dt){
   Vector3 start=arm.upper.position;
   var upperBase=(arm.elbow.position-start).normalized;var foreBase=(arm.wrist.position-arm.elbow.position).normalized;
   var upperNative=(loader.transform.rotation*faceTurn*(sourcePosition[arm.sourceElbow]-sourcePosition[arm.sourceUpper])).normalized;
   var foreNative=(loader.transform.rotation*faceTurn*(sourcePosition[arm.sourceWrist]-sourcePosition[arm.sourceElbow])).normalized;
   var hint=start+Vector3.Slerp(upperBase,upperNative,weight)*arm.a;
   var wrist=hint+Vector3.Slerp(foreBase,foreNative,weight)*arm.b;
   hint=OutsideTorso(hint,.025f);wrist=OutsideTorso(wrist,.065f);
   var localHint=loader.transform.InverseTransformPoint(hint);var localWrist=loader.transform.InverseTransformPoint(wrist);
   if(!arm.initialized){arm.smoothHint=loader.transform.InverseTransformPoint(arm.elbow.position);arm.smoothWrist=loader.transform.InverseTransformPoint(arm.wrist.position);arm.palm=Quaternion.Inverse(loader.transform.rotation)*arm.wrist.rotation;arm.initialized=true;}
   arm.smoothHint=Vector3.SmoothDamp(arm.smoothHint,localHint,ref arm.hintVelocity,.16f,1.5f,dt);
   arm.smoothWrist=Vector3.SmoothDamp(arm.smoothWrist,localWrist,ref arm.wristVelocity,.16f,1.5f,dt);
   hint=OutsideTorso(loader.transform.TransformPoint(arm.smoothHint),.025f);
   wrist=OutsideTorso(loader.transform.TransformPoint(arm.smoothWrist),.065f);
   Vector3 elbow,end;SolveArm(arm,wrist,hint,out elbow,out end);
   for(int step=0;step<18;step++){
    float penetration=0;
    for(int sample=0;sample<=8;sample++)penetration=Mathf.Min(penetration,Clearance(Vector3.Lerp(elbow,end,sample/8f),.04f));
    if(penetration>=0&&Clearance(elbow,.025f)>=0)break;
    float correction=Mathf.Clamp(-penetration*(torsoRadiusZ+.04f)*1.8f,.0004f,.025f);
    var forward=loader.transform.TransformVector(Vector3.back)*correction;
    hint=OutsideTorso(elbow,.03f)+forward;wrist=OutsideTorso(end,.065f)+forward;
    SolveArm(arm,wrist,hint,out elbow,out end);
   }
   arm.smoothHint=loader.transform.InverseTransformPoint(elbow);arm.smoothWrist=loader.transform.InverseTransformPoint(end);
   arm.upper.rotation=Quaternion.FromToRotation(arm.elbow.position-start,elbow-start)*arm.upper.rotation;
   arm.elbow.rotation=Quaternion.FromToRotation(arm.wrist.position-arm.elbow.position,end-arm.elbow.position)*arm.elbow.rotation;
   var palm=Quaternion.Inverse(loader.transform.rotation)*baseWorld[arm.wristMap];
   arm.palm=Quaternion.Slerp(arm.palm,palm,1-Mathf.Exp(-dt/.1f));arm.wrist.rotation=loader.transform.rotation*arm.palm;
  }
'''

original_create=build.create
def create(path,text):
    if path.name=='MainAvatarActions.cs':
        text=text.replace('public float a,b;}', 'public float a,b;public Vector3 smoothHint,smoothWrist,hintVelocity,wristVelocity;public Quaternion palm;public bool initialized;}')
        text=text.replace('foreach(var arm in arms)ApplyNativeArm(arm,1);','// Arms are solved after the continuous torso pose, in constrained position space.')
        text=text.replace('if(n=="頭"||n=="首"||IsLower(n))continue;', 'if(n=="頭"||n=="首"||IsArm(n)||IsLower(n))continue;')
        text=text.replace('   poseReady=true;MinArmClearance=ArmClearance();','   foreach(var arm in arms)ApplyNativeArm(arm,chosen>=0?1:0,dt);\n   poseReady=true;MinArmClearance=ArmClearance();')
        text=text.replace('Mathf.Sqrt(1-x*x)-.006f','Mathf.Sqrt(1-x*x)')
        start=text.index('  void ApplyNativeArm(ArmBinding arm,float weight)')
        end=text.index('  public float ArmClearance()',start)
        text=text[:start]+ARM+text[end:]
    original_create(path,text)
build.create=create

if __name__=='__main__':build.main()
