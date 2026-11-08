from pathlib import Path
import shutil
import json
import hashlib
import difflib

lab=Path(__file__).resolve().parent;main=lab.parent/'unity-client'
old=lab/'Project4';project=lab/'Project5';assert not project.exists()
changes={}
def edit(p):return (old/p).read_text(encoding='utf-8-sig')
def once(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)

p=Path('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs');s=edit(p)
s=s.replace('Quaternion[] speechRest,speechBasis;', 'Quaternion[] speechRest,speechBasis,naturalRest;')
s=s.replace('CalibrateSpeakingRest(loader.transform);','CalibrateSpeakingRest(loader.transform);CalibrateNaturalRest(loader.transform);')
s=once(s,'        void LateUpdate()', '''        void CalibrateNaturalRest(Transform root)
        {
            var saved=new Quaternion[bones.Length];naturalRest=new Quaternion[bones.Length];
            for(int i=0;i<bones.Length;i++)saved[i]=bones[i].localRotation;
            foreach(int arm in new[]{32,58})
            {
                int elbow=arm==32?35:61,wrist=arm==32?38:64;float side=arm==32?1:-1;
                var down=root.TransformDirection(new Vector3(side*.12f,-1,-.06f).normalized);
                bones[arm].rotation=Quaternion.FromToRotation(bones[elbow].position-bones[arm].position,down)*bones[arm].rotation;
                var forearm=root.TransformDirection(new Vector3(side*.045f,-1,-.20f).normalized);
                bones[elbow].rotation=Quaternion.FromToRotation(bones[wrist].position-bones[elbow].position,forearm)*bones[elbow].rotation;
            }
            for(int i=0;i<bones.Length;i++)naturalRest[i]=bones[i].localRotation;
            for(int i=0;i<bones.Length;i++)bones[i].localRotation=saved[i];
        }
        void LateUpdate()''')
s=once(s,'var calmRotation=ArmChain(index)?speechRest[index]:rotations[restFrame,i];','var calmRotation=ArmChain(index)?naturalRest[index]:rotations[restFrame,i];')
s=once(s,'                if(index==35||index==61)calmRotation*=Quaternion.Euler(8,0,0);\n','')
s=once(s,'''                float clearance=Mathf.Lerp(.33f,wardrobe!=null&&wardrobe.CurrentId=="swimsuit"?.19f:.29f,naturalBlend);
                if(side*target.x<clearance)''','''                float clearance=.33f*(1-naturalBlend);
                if(naturalBlend<.999f&&side*target.x<clearance)''')
changes[p]=s

p=Path('Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs');s=edit(p)
s=once(s,'rb.linearDamping=Mathf.Min(rb.linearDamping,2.5f);rb.angularDamping=Mathf.Min(rb.angularDamping,3.5f);',
'''rb.linearDamping=d.group==4?Mathf.Min(rb.linearDamping,2.5f):3.0f;
     rb.angularDamping=d.group==4?Mathf.Min(rb.angularDamping,3.5f):5.0f;''')
s=once(s,'dynamicFriction=d.group>=4?.12f:d.friction,staticFriction=d.group>=4?.16f:d.friction',
              'dynamicFriction=d.group>=4?.035f:d.friction,staticFriction=d.group>=4?.05f:d.friction')
s=once(s,'''    colliders[i].contactOffset=.001f;''','''    // Source capsules include end caps beyond the actual arm segment. At a
    // lowered arm these oversized supports sandwich fabric against the torso.
    // Fit total capsule height to the real skeleton, retaining contact coverage.
    if(d.group==0&&d.shape==2&&(d.bone==32||d.bone==58||d.bone==35||d.bone==61||d.bone==38||d.bone==64))
    {
     var capsule=(CapsuleCollider)colliders[i];int end=d.bone==32?35:d.bone==58?61:d.bone==35?38:d.bone==61?64:-1;
     float length=end>=0?Vector3.Distance(V(Loader.Data.bones[d.bone].positionScaled),V(Loader.Data.bones[end].positionScaled)):.07f;
     capsule.radius=Mathf.Min(capsule.radius,d.bone==32||d.bone==58?.032f:.026f);
     capsule.height=Mathf.Max(capsule.radius*2,length*.98f);
    }
    colliders[i].contactOffset=.001f;''')
s=once(s,'''     var force=mass*Vector3.ClampMagnitude(frequency*frequency*(pb-pa)+2*frequency*(b.GetPointVelocity(pb)-a.GetPointVelocity(pa)),18);''',
'''     // Backward PD avoids injecting energy when a sleeve is squeezed between
     // animated support and skirt. Bound force without resetting cloth positions.
     float denominator=1+2*frequency*fixedStep+frequency*frequency*fixedStep*fixedStep;
     var force=mass*Vector3.ClampMagnitude((frequency*frequency*(pb-pa)+
       (2*frequency+frequency*frequency*fixedStep)*(b.GetPointVelocity(pb)-a.GetPointVelocity(pa)))/denominator,12);''')
changes[p]=s

p=Path('Assets/MGFR/Skins/ClothPhysics/SwimsuitClothSolver.cs');s=edit(p)
s=once(s,'        readonly float scale;','''        readonly float scale;
        readonly Matrix4x4[] previousDrivers=new Matrix4x4[4];
        readonly Matrix4x4[] carryDrivers=new Matrix4x4[4];
        bool driverReady;''')
s=once(s,'''            for(int i=0;i<Particles.Length;i++)
            {var p=Particles[i];p.target=drivers[p.group].MultiplyPoint3x4(p.rest);Particles[i]=p;}
        }
        public void Reset()''', '''            if(driverReady)for(int g=0;g<4;g++)carryDrivers[g]=drivers[g]*previousDrivers[g].inverse;
            for(int i=0;i<Particles.Length;i++)
            {
                var p=Particles[i];
                if(driverReady)
                {
                    float follow=p.group<2?.85f:.65f;
                    p.position=Vector3.Lerp(p.position,carryDrivers[p.group].MultiplyPoint3x4(p.position),follow);
                    p.previous=Vector3.Lerp(p.previous,carryDrivers[p.group].MultiplyPoint3x4(p.previous),follow);
                }
                p.target=drivers[p.group].MultiplyPoint3x4(p.rest);Particles[i]=p;
            }
            for(int g=0;g<4;g++)previousDrivers[g]=drivers[g];driverReady=true;
        }
        public void Reset()''')
s=once(s,'''            p.position=point+normal*(capsule.radius/distance);Contacts++;''', '''            normal/=distance;
            var movement=p.position-p.previous;
            var correction=point+normal*capsule.radius-p.position;
            p.position+=correction;
            // Positional contact correction must not become next-frame rebound.
            // Preserve sliding, remove only velocity into the collider.
            p.previous+=correction+normal*Mathf.Min(0,Vector3.Dot(movement,normal));
            Contacts++;''')
changes[p]=s
p=Path('Assets/MGFR/Skins/ClothPhysics/SwimsuitClothRuntime.cs');s=edit(p)
s=once(s,'            for(int h=0;h<2;h++)\n            {\n                handCapsules[h].Clear();', '''            AddBody(b[35].position,b[38].position,.025f*scale);AddBody(b[61].position,b[64].position,.025f*scale);
            for(int h=0;h<2;h++)
            {
                handCapsules[h].Clear();''')
changes[p]=s

p=Path('Assets/MGFR/Scripts/Experience/NaturalIdle/NaturalIdleReview.cs');s=edit(p)
s=once(s,'public float maxLegacyPeriodDifferenceDeg,meanFrameMs;', '''public float maxLegacyPeriodDifferenceDeg,meanFrameMs;
            public float maxArmFromVerticalDeg,maxClothSpeedAfterSettling,maxClothSpeedAfterRelease,maxJointError;
            public string worstClothBody,worstJoint;''')
s=once(s,'            foreach(var bone in rig)report.finite&=', '''            foreach(int arm in new[]{32,58})
            {
                var direction=loader.transform.InverseTransformDirection(rig[arm==32?35:61].position-rig[arm].position);
                report.maxArmFromVerticalDeg=Mathf.Max(report.maxArmFromVerticalDeg,Vector3.Angle(Vector3.down,direction));
            }
            if(t>3&&t<13)
            {
                for(int j=0;j<physics.Bodies.Length;j++)if(!physics.Bodies[j].isKinematic&&physics.Data.bodies[j].group>=5)
                {
                    float speed=physics.Bodies[j].linearVelocity.magnitude;
                    if(speed>report.maxClothSpeedAfterSettling){report.maxClothSpeedAfterSettling=speed;report.worstClothBody=physics.Data.bodies[j].name;}
                    if(t>11)report.maxClothSpeedAfterRelease=Mathf.Max(report.maxClothSpeedAfterRelease,speed);
                }
                foreach(var joint in physics.Joints)
                {
                    float error=Vector3.Distance(joint.transform.TransformPoint(joint.anchor),joint.connectedBody.transform.TransformPoint(joint.connectedAnchor));
                    if(error>report.maxJointError){report.maxJointError=error;report.worstJoint=joint.name;}
                }
            }
            foreach(var bone in rig)report.finite&=''')
s=once(s,'report.originalReady&&report.swimsuitReady&&report.returnedToOriginal;',
'''report.originalReady&&report.swimsuitReady&&report.returnedToOriginal&&
                report.maxArmFromVerticalDeg<14&&report.maxClothSpeedAfterRelease<.9f&&report.maxJointError<.025f;''')
changes[p]=s

def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old) in changes]
for folder in ('Assets','Packages','ProjectSettings'):shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)
print(project)
