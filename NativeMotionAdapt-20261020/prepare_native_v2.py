from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'NativeClothCoordinator.cs').read_text(encoding='utf-8')
text=text.replace('  readonly Matrix4x4[] previous=', '  Vector3[] carryPosition,carryPrevious;readonly Matrix4x4[] carry=new Matrix4x4[4];\n  readonly Matrix4x4[] previous=')
text=text.replace('public int AddedCapsules {get;private set;}', 'public int AddedCapsules {get;private set;}public float ResidualPenetration {get;private set;}')
text=text.replace('   var positions=new Vector3[solver.Particles.Length];var oldPositions=new Vector3[positions.Length];', '   if(carryPosition==null||carryPosition.Length!=solver.Particles.Length){carryPosition=new Vector3[solver.Particles.Length];carryPrevious=new Vector3[solver.Particles.Length];}\n   var positions=carryPosition;var oldPositions=carryPrevious;\n   if(previousReady)for(int g=0;g<4;g++)carry[g]=drivers[g]*previous[g].inverse;')
text=text.replace('var carry=drivers[p.group]*previous[p.group].inverse;positions[i]=carry.MultiplyPoint3x4(p.position);oldPositions[i]=carry.MultiplyPoint3x4(p.previous);', 'positions[i]=carry[p.group].MultiplyPoint3x4(p.position);oldPositions[i]=carry[p.group].MultiplyPoint3x4(p.previous);')
text=text.replace('   solver.WriteVertices(', '   FinishBodyContacts(solver);\n   solver.WriteVertices(')
text=text.replace('visual.RecalculateTangents();', 'if(frames%3==0)visual.RecalculateTangents();')
index=text.index('  void Add(Vector3 a,Vector3 b,float r)')
text=text[:index]+'''  void FinishBodyContacts(SwimsuitClothSolver solver){
   for(int iteration=0;iteration<2;iteration++)for(int i=0;i<solver.Particles.Length;i++){
    var p=solver.Particles[i];if(p.inverseMass==0||!solver.EnabledGroups[p.group])continue;
    foreach(var capsule in body){var axis=capsule.b-capsule.a;float t=axis.sqrMagnitude>1e-10f?Mathf.Clamp01(Vector3.Dot(p.position-capsule.a,axis)/axis.sqrMagnitude):0;var center=capsule.a+axis*t;var normal=p.position-center;float squared=normal.sqrMagnitude;
     if(squared>=capsule.radius*capsule.radius||squared<1e-12f)continue;var correction=normal*(capsule.radius/Mathf.Sqrt(squared)-1);p.position+=correction;p.previous+=correction;
    }solver.Particles[i]=p;
   }
   ResidualPenetration=0;
   for(int i=0;i<solver.Particles.Length;i++){var p=solver.Particles[i];if(p.inverseMass==0||!solver.EnabledGroups[p.group])continue;
    foreach(var capsule in body){var axis=capsule.b-capsule.a;float t=axis.sqrMagnitude>1e-10f?Mathf.Clamp01(Vector3.Dot(p.position-capsule.a,axis)/axis.sqrMagnitude):0;float depth=capsule.radius-Vector3.Distance(p.position,capsule.a+axis*t);ResidualPenetration=Mathf.Max(ResidualPenetration,depth);}
   }
  }
'''+text[index:]
with (ROOT/'NativeClothCoordinator-v2.cs').open('x',encoding='utf-8') as f:f.write(text)
source=(ROOT/'build_native.py').read_text(encoding='utf-8').replace("ROOT/'NativeClothCoordinator.cs'","ROOT/'NativeClothCoordinator-v2.cs'")
exec(compile(source,str(ROOT/'build_native.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'build_native.py')})
