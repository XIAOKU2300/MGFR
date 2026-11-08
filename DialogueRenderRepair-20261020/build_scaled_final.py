"""Normalize cloth simulation while preserving real world state for existing interactions."""
from pathlib import Path
import json
import subprocess
import hashlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BASE=HERE/'Current'
OUT=HERE/'Final'
OUT.mkdir(exist_ok=False)
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data.encode('utf-8') if isinstance(data,str) else data)
source=OUT/'Source';source.mkdir()
for path in (BASE/'Source').glob('*.cs'):
    text=path.read_text(encoding='utf-8')
    if path.name=='NativeClothCoordinator-production.cs':
        old='''   if(hands.Physics.Simulate)solver.Step(delta,stepBody,handContacts,skins.Loader.transform.TransformDirection(new Vector3(.08f,0,.025f)));else solver.Reset();
   FinishBodyContacts(solver);'''
        new='''   float currentScale=Mathf.Abs(skins.Loader.transform.lossyScale.x);
   float referenceScale=(float)SolverScaleField.GetValue(solver);float factor=referenceScale/Mathf.Max(.001f,currentScale);
   var wind=skins.Loader.transform.TransformDirection(new Vector3(.08f,0,.025f));
   if(hands.Physics.Simulate&&Mathf.Abs(factor-1)>.00001f){
    // The solver's rest lengths and travel are fixed at its creation scale.
    // Simulate in that metric, then restore real world state before every other
    // system reads particles, grips, targets or the visible cloth surface.
    var origin=skins.Loader.transform.position;var normalize=Matrix4x4.TRS(origin,Quaternion.identity,Vector3.one*factor)*Matrix4x4.Translate(-origin);
    ReframeSolver(solver,normalize);ScaleContacts(stepBody,scaledStepBody,normalize,factor);ScaleContacts(body,scaledFullBody,normalize,factor);
    for(int h=0;h<2;h++)ScaleContacts(handContacts[h],scaledHands[h],normalize,factor);
    var realBody=body;body=scaledFullBody;
    try{solver.Step(delta,scaledStepBody,scaledHands,wind);FinishBodyContacts(solver);ResidualPenetration/=factor;}
    finally{body=realBody;ReframeSolver(solver,normalize.inverse);}
   }else{if(hands.Physics.Simulate)solver.Step(delta,stepBody,handContacts,wind);else solver.Reset();FinishBodyContacts(solver);}'''
        assert text.count(old)==1
        text=text.replace(old,new)
        text=text.replace('var side=root.right*.055f;', 'var side=root.TransformVector(Vector3.right*.055f);')
        methods='''  static readonly FieldInfo SolverScaleField=typeof(SwimsuitClothSolver).GetField("scale",BindingFlags.Instance|BindingFlags.NonPublic);
  readonly List<SwimsuitClothSolver.Capsule> scaledStepBody=new List<SwimsuitClothSolver.Capsule>(),scaledFullBody=new List<SwimsuitClothSolver.Capsule>();
  readonly List<SwimsuitClothSolver.Capsule>[] scaledHands={new List<SwimsuitClothSolver.Capsule>(),new List<SwimsuitClothSolver.Capsule>()};
  static void ReframeSolver(SwimsuitClothSolver solver,Matrix4x4 transform){
   for(int i=0;i<solver.Particles.Length;i++){var p=solver.Particles[i];p.position=transform.MultiplyPoint3x4(p.position);p.previous=transform.MultiplyPoint3x4(p.previous);p.target=transform.MultiplyPoint3x4(p.target);solver.Particles[i]=p;}
   for(int h=0;h<2;h++){var grip=solver.Grips[h];if(grip.particle<0)continue;grip.target=transform.MultiplyPoint3x4(grip.target);grip.offset=transform.MultiplyVector(grip.offset);solver.Grips[h]=grip;}
  }
  static void ScaleContacts(List<SwimsuitClothSolver.Capsule> input,List<SwimsuitClothSolver.Capsule> output,Matrix4x4 transform,float factor){output.Clear();foreach(var c in input)output.Add(new SwimsuitClothSolver.Capsule{a=transform.MultiplyPoint3x4(c.a),b=transform.MultiplyPoint3x4(c.b),radius=c.radius*factor});}
'''
        text=text.replace('  void OnDestroy(){',methods+'  void OnDestroy(){')
    if path.name=='NativeAvatarActions-main.cs':
        text=text.replace('var go=new GameObject("Native retargeted avatar actions");','if(Array.IndexOf(args,"-mgfr-scale-review")>=0)new GameObject("Proportional cloth scale acceptance").AddComponent<MGFR.Repairs.ClothScaleReview>();\n   var go=new GameObject("Native retargeted avatar actions");')
    write(source/path.name,text)
write(source/'ClothScaleReview.cs',(HERE/'ClothScaleReview.cs').read_bytes())
managed=BASE/'Player/MGFR_Data/Managed';build=OUT/'Build';build.mkdir();plugin=build/'MGFR.StructuredVoiceFinal.dll'
options=['/nologo','/target:library','/nostdlib+','/langversion:latest','/out:'+str(plugin)]
options+=['/reference:'+str(p) for p in managed.glob('*.dll') if p.name!=plugin.name]
options+=[str(p) for p in source.glob('*.cs')]
rsp=build/'compile.rsp';write(rsp,'\n'.join('"'+p+'"' for p in options))
subprocess.run([str(ROOT/'Editor/Data/NetCoreRuntime/dotnet.exe'),str(ROOT/'Editor/Data/DotNetSdkRoslyn/csc.dll'),'@'+str(rsp)],check=True)
for path in (BASE/'Player').rglob('*'):
    if not path.is_file():continue
    rel=path.relative_to(BASE/'Player')
    if rel.as_posix() in ['MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll','MGFR_Data/Managed/MGFR.StructuredVoiceFinal.pdb']:continue
    write(OUT/'Player'/rel,path.read_bytes())
write(OUT/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll',plugin.read_bytes())
for path in (BASE/'Voice').glob('*.py'):write(OUT/'Voice'/path.name,path.read_bytes())
write(OUT/'receipt.json',json.dumps({'base':str(BASE),'moduleSha256':hashlib.sha256(plugin.read_bytes()).hexdigest(),'scalePhysics':'Solver metric normalized per frame; world-space state preserved for existing grabs and wardrobe'},indent=2))
print('FINAL_SCALED_REPAIR_PACKAGE',OUT/'Player/MGFR.exe')
