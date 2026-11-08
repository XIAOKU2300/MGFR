from pathlib import Path
import shutil

lab=Path(__file__).resolve().parent;old=lab/'Project2';project=lab/'Project3';assert not project.exists()
changes={}
p=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs');s=(old/p).read_text(encoding='utf-8-sig')
s=s.replace('  bool[] longHair;', '  bool[] longHair;\n  const float HairGravity=6.5f,HairBend=.10f;')
s=s.replace('float swing=Bodies[d.a].isKinematic?50:38;', 'float swing=Bodies[d.a].isKinematic?24:30;')
s=s.replace('''     float spring=b.mass*.12f;
     float inertia=Mathf.Max(b.inertiaTensor.x,Mathf.Max(b.inertiaTensor.y,b.inertiaTensor.z));
     j.slerpDrive=new JointDrive{positionSpring=spring,positionDamper=2*Mathf.Sqrt(spring*inertia),maximumForce=b.mass*.5f};''', '''     // Support is proportional to the weight and lever arm of the remaining
     // strand, not only the mass of this tiny segment. This retains a gentle
     // authored arc without rigid bars or collapsing the whole strand straight.
     float moment=0,subtreeInertia=0;
     for(int k=d.b;k<count&&longHair[k]&&Data.bodies[k].name[0]==Data.bodies[d.b].name[0];k++)
     {
      var lever=V(Data.bodies[k].position)*.08f-jointPoint;
      moment+=Bodies[k].mass*HairGravity*new Vector2(lever.x,lever.z).magnitude;
      subtreeInertia+=Bodies[k].mass*lever.sqrMagnitude;
     }
     float spring=Mathf.Max(.0002f,moment/HairBend);
     j.slerpDrive=new JointDrive{positionSpring=spring,
       positionDamper=.45f*2*Mathf.Sqrt(spring*Mathf.Max(subtreeInertia,.000001f)),maximumForce=Mathf.Max(.001f,moment*2)};''')
s=s.replace('FlexibleLongHair&&longHair[i]?9.81f:1.8f','FlexibleLongHair&&longHair[i]?HairGravity:1.8f')
changes[p]=s
p=Path('Assets/MGFR/Scripts/Experience/NaturalIdle/HairFallReview.cs');s=(old/p).read_text(encoding='utf-8-sig')
s=s.replace('report.leftHorizontalM<.30f&&report.rightHorizontalM<.30f&&report.leftDropM>.65f&&report.rightDropM>.65f',
'''report.leftHorizontalM>.16f&&report.rightHorizontalM>.16f&&report.leftHorizontalM<.40f&&report.rightHorizontalM<.40f&&report.leftDropM>.80f&&report.rightDropM>.80f''')
changes[p]=s
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old) in changes]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print(project)
