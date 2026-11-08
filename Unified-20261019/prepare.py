from pathlib import Path
import hashlib,json,shutil,difflib

lab=Path(__file__).resolve().parent;root=lab.parent
base=root/'ShoeEasy-20261019/Project';motion=root/'HairFall-20261019/Project3';project=lab/'Project1'
assert not project.exists()
changes={}
def once(s,a,b):
    assert s.count(a)==1,a[:100]
    return s.replace(a,b)
def text(p):return (base/p).read_text(encoding='utf-8-sig')

# Verify the current complete feature base before incorporating motion-only code.
for rel in ('Assets/MGFR/Wardrobe/WardrobeLiveRuntime.cs','Assets/MGFR/Wardrobe/ShoeFootPose.cs',
            'Assets/StreamingAssets/skins/si-swimsuit-shoes/foot-pose.json',
            'Assets/StreamingAssets/wardrobe/with_shoes/wardrobe.json'):
    if not (base/rel).exists() and rel.endswith('wardrobe.json'):
        assert list((base/'Assets/StreamingAssets/wardrobe/with_shoes').glob('*.json'))
    else:assert (base/rel).exists(),rel

p=Path('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs')
s=(motion/p).read_text(encoding='utf-8-sig')
s=once(s,'        float naturalBlend=1;', '''        float naturalBlend=1;
        public NaturalLowerBody Lower {get;}=new NaturalLowerBody();
        public LowerBodyPose LowerPose {get;private set;}
        public float LowerStrength {get;private set;}
        float legClock,legRate=1;''')
s=once(s,'            if(Playing)clock+=Time.deltaTime;', '''            var wardrobeLive=MGFR.Wardrobe.WardrobeLiveRuntime.Instance;
            bool handling=false;
            if(wardrobeLive!=null&&wardrobeLive.IsReady)for(int h=0;h<2;h++)
                handling|=wardrobeLive.Pending(h)!=null||wardrobeLive.Held(h)!=null;
            legRate=Mathf.MoveTowards(legRate,handling?0:1,Time.deltaTime/.25f);
            if(Playing){clock+=Time.deltaTime;legClock+=Time.deltaTime*legRate;}''')
s=once(s,'            float poseDelta=', '            MGFR.Wardrobe.ShoeFootPose.Instance?.UndoLift();\n            float poseDelta=')
s=once(s,'            Phase=Mathf.Repeat(seconds,Duration)*fps;', '''            LowerStrength=naturalBlend*(1-.35f*speech.Weight);
            LowerPose=Lower.Sample(frameDelta>=0||ManualTime>=0?seconds:legClock,LowerStrength);
            Phase=Mathf.Repeat(seconds,Duration)*fps;''')
s=once(s,'                var calmPosition=positions[restFrame,i];', '''                var calmPosition=positions[restFrame,i];
                // Rest IK targets remove the source costume's permanent lifted
                // foot. Authored foot swings and shoe height are layered later.
                if(index==0||index==1||index==3||(index>=6&&index<=11))calmPosition=Vector3.zero;''')
s=once(s,'                position=Vector3.Lerp(position,calmPosition,naturalBlend);', '''                if(index==0||index==1||index==3||(index>=6&&index<=11))calmRotation=Quaternion.identity;
                position=Vector3.Lerp(position,calmPosition,naturalBlend);''')
s=once(s,'                // Sleeves must have time to follow the arm during both idle and', '''                if(index==5)position+=LowerPose.Hips;
                if(index==12)rotation*=Quaternion.Euler(LowerPose.Pelvis);
                // Sleeves must have time to follow the arm during both idle and''')
changes[p]=s

# Physics has no wardrobe-specific delta; compare against its known parent to
# ensure taking the reviewed hair/cloth implementation cannot remove features.
p=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs')
assert (base/p).read_bytes()==(root/'unity-client'/p).read_bytes()
changes[p]=(motion/p).read_text(encoding='utf-8-sig')

# Keep the newer group suspension / wardrobe ownership APIs in the XPBD solver.
p=Path('Assets/MGFR/Skins/ClothPhysics/SwimsuitClothSolver.cs');s=text(p)
new=(motion/p).read_text(encoding='utf-8-sig')
s=once(s,'        readonly float scale;', '''        readonly float scale;
        readonly Matrix4x4[] previousDrivers=new Matrix4x4[4];
        readonly Matrix4x4[] carryDrivers=new Matrix4x4[4];
        bool driverReady;''')
start='        public void SetTargets(Matrix4x4[] drivers)';end='        public void Reset()'
a=s.index(start);b=s.index(end,a);c=new.index(start);d=new.index(end,c);s=s[:a]+new[c:d]+s[b:]
s=once(s,'            p.position=point+normal*(capsule.radius/distance);Contacts++;', '''            normal/=distance;var movement=p.position-p.previous;
            var correction=point+normal*capsule.radius-p.position;p.position+=correction;
            p.previous+=correction+normal*Mathf.Min(0,Vector3.Dot(movement,normal));Contacts++;''')
changes[p]=s
p=Path('Assets/MGFR/Skins/ClothPhysics/SwimsuitClothRuntime.cs');s=text(p)
s=once(s,'''                float gust=.35f+.25f*Mathf.Sin(Time.time*1.7f);
                var wind=skins.Loader.transform.TransformDirection(new Vector3(gust,.07f,Mathf.Sin(Time.time*.8f)*.25f));''', '''                var idle=skins.Loader.GetComponent<MGFR.Experience.IdleMotionPlayer>();
                var air=idle!=null&&idle.NaturalIdle?idle.Natural.Air(idle.MotionSeconds)*2:new Vector3(.15f,0,.05f);
                var wind=skins.Loader.transform.TransformDirection(air);''')
s=once(s,'            for(int h=0;h<2;h++)\n            {\n                handCapsules[h].Clear();', '''            AddBody(b[35].position,b[38].position,.025f*scale);AddBody(b[61].position,b[64].position,.025f*scale);
            for(int h=0;h<2;h++)
            {
                handCapsules[h].Clear();''')
changes[p]=s

p=Path('Assets/MGFR/Scripts/Experience/LegPlantSolver.cs');s=text(p)
s=once(s,'        Transform[] bones;', '''        Transform[] bones;
        IdleMotionPlayer motion;SiCharacterLoader loader;
        public readonly Vector3[] Goals=new Vector3[2];
        public readonly float[] Pitches=new float[2];''')
s=once(s,'            bones=idle.GetComponent<SiCharacterLoader>().Renderer.bones;',
'''            motion=idle;loader=idle.GetComponent<SiCharacterLoader>();bones=loader.Renderer.bones;''')
s=once(s,'            Vector3 goal=bones[target].position+lift-hip.position;', '''            int side=h==21?0:1;var pose=motion.LowerPose;
            float pitch=side==0?pose.LeftPitch:pose.RightPitch,yaw=side==0?pose.LeftYaw:pose.RightYaw;
            var offset=side==0?pose.Left:pose.Right;
            var frame=bones[0].parent;
            // Heel rise pivots around the forefoot. Include the current shoe
            // height, so the heel and toes behave coherently in either foot shape.
            var aRest=loader.Data.bones[a].positionScaled;var toeRest=loader.Data.bones[toe].positionScaled;
            var fromBall=new Vector3(0,aRest[1]+(shoePose?shoes.Height*shoes.Weights[side]:0),aRest[2]-toeRest[2]);
            if(pitch<0)offset+=Quaternion.Euler(pitch,0,0)*fromBall-fromBall;
            var goalWorld=bones[target].position+lift+frame.TransformVector(offset);
            Goals[side]=goalWorld;Pitches[side]=pitch;
            Vector3 goal=goalWorld-hip.position;''')
s=once(s,'            if(shoePose){ankle.rotation=bones[0].parent.rotation;bones[toe].localRotation=Quaternion.identity;}',
'''            if(shoePose||motion.LowerStrength>.001f)
            {
                ankle.rotation=bones[0].parent.rotation*Quaternion.Euler(pitch,yaw,0);
                // Toe flex counters heel lift and keeps the toe pad in contact.
                bones[toe].localRotation=Quaternion.Euler(pitch<0?-pitch*.7f:0,0,0);
            }''')
s=once(s,'Vector3.Distance(ankle.position,bones[target].position+lift)', 'Vector3.Distance(ankle.position,goalWorld)')
changes[p]=s
p=Path('Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs');s=text(p)
s=once(s,'a=="-mgfr-wardrobe-review"','a=="-mgfr-unified-review"||a=="-mgfr-shoe-review"||a=="-mgfr-wardrobe-review"')
changes[p]=s

def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(base) in changes]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(base/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
module=project/'Assets/MGFR/Scripts/Experience/NaturalIdle';module.mkdir()
for name in ('NaturalIdlePose.cs','IdleAirMotion.cs'):
    shutil.copyfile(motion/'Assets/MGFR/Scripts/Experience/NaturalIdle'/name,module/name)
for p in (lab/'Source').glob('*.cs'):shutil.copyfile(p,module/p.name)
shutil.copyfile(root/'NaturalIdle-20261019/IdleBuild.cs',project/'Assets/MGFR/Editor/IdleBuild.cs')
hashes={str(base/p):hashlib.sha256((base/p).read_bytes()).hexdigest() for p in changes}
with (lab/'base-hashes.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2)
patch=[]
for p,s in changes.items():patch+=difflib.unified_diff(text(p).splitlines(True),s.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix())
with (lab/'integration.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
with (lab/'desktop-no-runtime.json').open('x',encoding='ascii') as f:f.write('{}\n')
print(project)
