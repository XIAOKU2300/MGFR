from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'NativeClothCoordinator-v2.cs').read_text(encoding='utf-8')
text=text.replace('  void FinishBodyContacts(SwimsuitClothSolver solver){', '  void UnusedOldContacts(SwimsuitClothSolver solver){',1)
start=text.index('  void UnusedOldContacts(');end=text.index('  void Add(Vector3 a,Vector3 b,float r)',start)
text=text[:start]+'''  struct ContactShape {public Vector3 a,axis,min,max;public float radius,invLength;}
  readonly ContactShape[] shapes=new ContactShape[80];
  void FinishBodyContacts(SwimsuitClothSolver solver){
   int count=Mathf.Min(body.Count,shapes.Length);
   for(int i=0;i<count;i++){var c=body[i];var axis=c.b-c.a;var margin=Vector3.one*c.radius;shapes[i]=new ContactShape{a=c.a,axis=axis,min=Vector3.Min(c.a,c.b)-margin,max=Vector3.Max(c.a,c.b)+margin,radius=c.radius,invLength=axis.sqrMagnitude>1e-10f?1/axis.sqrMagnitude:0};}
   for(int iteration=0;iteration<2;iteration++)for(int i=0;i<solver.Particles.Length;i++){
    var p=solver.Particles[i];if(p.inverseMass==0||!solver.EnabledGroups[p.group])continue;
    for(int c=0;c<count;c++){var shape=shapes[c];var v=p.position;if(v.x<shape.min.x||v.x>shape.max.x||v.y<shape.min.y||v.y>shape.max.y||v.z<shape.min.z||v.z>shape.max.z)continue;
     float t=Mathf.Clamp01(Vector3.Dot(v-shape.a,shape.axis)*shape.invLength);var normal=v-(shape.a+shape.axis*t);float squared=normal.sqrMagnitude;
     if(squared>=shape.radius*shape.radius||squared<1e-12f)continue;var correction=normal*(shape.radius/Mathf.Sqrt(squared)-1);p.position+=correction;p.previous+=correction;
    }solver.Particles[i]=p;
   }
   // A bounded diagnostic sample; do not add a full collision sweep to every display frame.
   if(frames%30!=0)return;ResidualPenetration=0;
   for(int i=0;i<solver.Particles.Length;i++){var p=solver.Particles[i];if(p.inverseMass==0||!solver.EnabledGroups[p.group])continue;
    for(int c=0;c<count;c++){var shape=shapes[c];var v=p.position;if(v.x<shape.min.x||v.x>shape.max.x||v.y<shape.min.y||v.y>shape.max.y||v.z<shape.min.z||v.z>shape.max.z)continue;
     float t=Mathf.Clamp01(Vector3.Dot(v-shape.a,shape.axis)*shape.invLength);float depth=shape.radius-Vector3.Distance(v,shape.a+shape.axis*t);ResidualPenetration=Mathf.Max(ResidualPenetration,depth);}
   }
  }
'''+text[end:]
with (ROOT/'NativeClothCoordinator-v3.cs').open('x',encoding='utf-8') as f:f.write(text)
test=(ROOT/'NativeAcceptance.cs').read_text(encoding='utf-8')
test=test.replace('clothMeanMs;', 'clothMeanMs,clothResidual;')
test=test.replace('   for(int i=0;i<bones.Length;i++){float angle=', '   if(current.frames==1){for(int i=0;i<bones.Length;i++){previous[i]=bones[i].localRotation;positions[i]=skins.Loader.transform.InverseTransformPoint(bones[i].position);}return;}\n   for(int i=0;i<bones.Length;i++){float angle=')
test=test.replace('if(cloth!=null)current.clothMeanMs+=cloth.LastMilliseconds;', 'if(cloth!=null){current.clothMeanMs+=cloth.LastMilliseconds;current.clothResidual=Mathf.Max(current.clothResidual,cloth.ResidualPenetration);}')
with (ROOT/'NativeAcceptance-v3.cs').open('x',encoding='utf-8') as f:f.write(test)
source=(ROOT/'build_native.py').read_text(encoding='utf-8').replace("ROOT/'NativeClothCoordinator.cs'","ROOT/'NativeClothCoordinator-v3.cs'").replace("ROOT/'NativeAcceptance.cs'","ROOT/'NativeAcceptance-v3.cs'")
exec(compile(source,str(ROOT/'build_native.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'build_native.py')})
