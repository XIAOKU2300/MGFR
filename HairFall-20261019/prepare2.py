from pathlib import Path
import shutil
import difflib

lab=Path(__file__).resolve().parent;old=lab/'Project1';project=lab/'Project2';assert not project.exists()
changes={}
p=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs');s=(old/p).read_text(encoding='utf-8-sig')
s=s.replace('''   var hairVelocities=new Vector3[Bodies.Length];var hairSpins=new Vector3[Bodies.Length];''', '''   var hairVelocities=new Vector3[Bodies.Length];var hairSpins=new Vector3[Bodies.Length];
   var oldHairAnchors=new Vector3[Bodies.Length];var oldHairTurns=new Quaternion[Bodies.Length];''')
s=s.replace('''    hairVelocities[i]=Bodies[i].linearVelocity;hairSpins[i]=Bodies[i].angularVelocity;''', '''    hairVelocities[i]=Bodies[i].linearVelocity;hairSpins[i]=Bodies[i].angularVelocity;
    int a=anchors[i];oldHairAnchors[i]=Bodies[a].position;oldHairTurns[i]=Bodies[a].rotation;''')
s=s.replace('''    Bodies[i].position=hairPositions[i];Bodies[i].rotation=hairRotations[i];
    Bodies[i].linearVelocity=hairVelocities[i];Bodies[i].angularVelocity=hairSpins[i];Bodies[i].WakeUp();''', '''    // Barefoot skin lowers the rest skeleton by about 6.3 cm. Carry the
    // settled chain through its own attachment frame, rather than leaving its
    // dynamic points behind while the fixed hair root jumps to the new height.
    int a=anchors[i];var turn=Bodies[a].rotation*Quaternion.Inverse(oldHairTurns[i]);
    Bodies[i].position=Bodies[a].position+turn*(hairPositions[i]-oldHairAnchors[i]);
    Bodies[i].rotation=turn*hairRotations[i];
    Bodies[i].linearVelocity=turn*hairVelocities[i];Bodies[i].angularVelocity=turn*hairSpins[i];Bodies[i].WakeUp();''')
changes[p]=s
p=Path('Assets/MGFR/Scripts/Experience/NaturalIdle/HairFallReview.cs');s=(old/p).read_text(encoding='utf-8-sig')
s=s.replace('maxSkinSwitchJumpM','maxSkinSwitchShapeJumpM')
s=s.replace('previousTips[i]=physics.Bodies[tips[i]].position;', 'previousTips[i]=physics.Bodies[tips[i]].position-physics.Bodies[roots[i]].position;')
s=s.replace('''                var tip=physics.Bodies[tips[s]].position;
                if(t>12.9f''', '''                var tip=physics.Bodies[tips[s]].position;
                var shape=tip-physics.Bodies[roots[s]].position;
                if(t>12.9f''')
s=s.replace('Vector3.Distance(tip,previousTips[s])','Vector3.Distance(shape,previousTips[s])')
s=s.replace('previousTips[s]=tip;','previousTips[s]=shape;')
s=s.replace('report.maxSkinSwitchShapeJumpM<.08f','report.maxSkinSwitchShapeJumpM<.02f')
changes[p]=s
def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old) in changes]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print(project)
