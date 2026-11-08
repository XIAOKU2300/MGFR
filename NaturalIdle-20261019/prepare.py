"""Create a new candidate using exclusive writes; never edit the live project."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

lab = Path(__file__).resolve().parent
main = lab.parent / 'unity-client'
project = lab / 'Project1'
assert not project.exists(), 'Candidate must be a new path'
changes = {}
def read(relative):
    return (main / relative).read_text(encoding='utf-8-sig')
def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

p = Path('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs')
s = read(p)
s = replace_once(s, '        float clock;', '''        float clock;
        public bool NaturalIdle = System.Array.IndexOf(System.Environment.GetCommandLineArgs(), "-mgfr-legacy-idle") < 0;
        public NaturalIdlePose Natural {get;} = new NaturalIdlePose();
        public float MotionSeconds {get;private set;}
        public float LastNaturalMilliseconds {get;private set;}
        float naturalBlend=1;
        void Update(){if(Input.GetKeyDown(KeyCode.F6))NaturalIdle=!NaturalIdle;}''')
s = replace_once(s, '            Phase=Mathf.Repeat(seconds,Duration)*fps;', '''            long started=System.Diagnostics.Stopwatch.GetTimestamp();
            MotionSeconds=seconds;
            naturalBlend=Mathf.MoveTowards(naturalBlend,NaturalIdle?1:0,poseDelta/.9f);
            Phase=Mathf.Repeat(seconds,Duration)*fps;''')
s = replace_once(s, '                if(SpeechMotionState.AffectsBone(index)||ArmChain(index))', '''                int restFrame=Mathf.Min((int)(.9f*fps),frames-1);
                var calmPosition=positions[restFrame,i];
                var calmRotation=ArmChain(index)?speechRest[index]:rotations[restFrame,i];
                position=Vector3.Lerp(position,calmPosition,naturalBlend);
                rotation=Quaternion.Slerp(rotation,calmRotation,naturalBlend);
                if(SpeechMotionState.AffectsBone(index)||ArmChain(index))''')
s = replace_once(s, '                // Sleeves must have time to follow the arm during both idle and', '''                if(naturalBlend>0)
                {
                    float weight=naturalBlend*(ArmChain(index)?1-speech.Weight:1-.35f*speech.Weight);
                    position+=Natural.Translation(index,seconds)*weight;
                    rotation*=Quaternion.Euler(Natural.Angles(index,seconds)*weight);
                }
                // Sleeves must have time to follow the arm during both idle and''')
s = replace_once(s, '                attention.SubmitHeadGesture(Vector3.Lerp(e,SpeechMotionState.HeadOffset(clock)+Gestures.Head,speech.Weight),Time.unscaledTime);', '''                e=Vector3.Lerp(e,Natural.Head(seconds),naturalBlend);
                attention.SubmitHeadGesture(Vector3.Lerp(e,SpeechMotionState.HeadOffset(clock)+Gestures.Head,speech.Weight),Time.unscaledTime);''')
s = replace_once(s, '        void OnDestroy(){if(client!=null)client.SentenceQueued-=Gestures.Queue;}', '''        void OnDestroy(){if(client!=null)client.SentenceQueued-=Gestures.Queue;}''')
# Time the entire pose calculation, including existing interpolation/arm clearance.
s = replace_once(s, '''            }
        }
        void OnDestroy()''', '''            }
            LastNaturalMilliseconds=(float)((System.Diagnostics.Stopwatch.GetTimestamp()-started)*1000d/System.Diagnostics.Stopwatch.Frequency);
        }
        void OnDestroy()''')
changes[p] = s

# Carry forward the already working independent swimsuit fabric module, using
# CURRENT main as the base so intervening shoe/hand/render fixes survive.
p = Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs')
s = read(p)
s = replace_once(s, '  public HandJointSource Source {get;private set;}',
                 '  public HandJointSource Source {get;private set;}\n  public System.Func<int,bool> ExternalClothGrab;')
s = replace_once(s, '''  void AcquireHand(int h,bool afterPhysics)
  {
   if(!acquisitionPending[h])return;''', '''  void AcquireHand(int h,bool afterPhysics)
  {
   if(ExternalClothGrab!=null&&ExternalClothGrab(h))
   {Release(h);blockedUntilOpen[h]=true;GrabStatus[h]="泳装布料抓取中";return;}
   if(!acquisitionPending[h])return;''')
s = replace_once(s, '(GrabbedBody[0]>=0||GrabbedBody[1]>=0?"抓取中":"无")',
    '(GrabbedBody[0]>=0||GrabbedBody[1]>=0||(ExternalClothGrab!=null&&(ExternalClothGrab(0)||ExternalClothGrab(1)))?"抓取中":"无")')
changes[p] = s

p = Path('Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs')
s=read(p)
s=replace_once(s, 'a=="-mgfr-cloth-motion-review"', 'a=="-mgfr-natural-idle-review"||a=="-mgfr-cloth-motion-review"')
changes[p]=s

cloth=lab.parent/'SwimsuitCloth-20261019/Project3/Assets/MGFR/Skins/ClothPhysics'
assert cloth.is_dir()
for source in cloth.glob('*.cs'):
    p=Path('Assets/MGFR/Skins/ClothPhysics')/source.name
    s=source.read_text(encoding='utf-8-sig')
    if source.name=='SwimsuitClothRuntime.cs':
        s=replace_once(s, '''                float gust=.35f+.25f*Mathf.Sin(Time.time*1.7f);
                var wind=skins.Loader.transform.TransformDirection(new Vector3(gust,.07f,Mathf.Sin(Time.time*.8f)*.25f));''', '''                var idle=skins.Loader.GetComponent<MGFR.Experience.IdleMotionPlayer>();
                var air=idle!=null&&idle.NaturalIdle?idle.Natural.Air(idle.MotionSeconds)*2:
                    new Vector3(.15f,0,.05f);
                var wind=skins.Loader.transform.TransformDirection(air);''')
    changes[p]=s

def ignore(directory, names):
    return [name for name in names if (Path(directory)/name).relative_to(main) in changes]
for name in ('Assets', 'Packages', 'ProjectSettings'):
    shutil.copytree(main/name, project/name, ignore=ignore)
for p,s in changes.items():
    target=project/p
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf-8',newline='\n') as f:f.write(s)
module=project/'Assets/MGFR/Scripts/Experience/NaturalIdle'
module.mkdir()
for source in (lab/'Source').glob('*.cs'):
    shutil.copyfile(source,module/source.name)
shutil.copyfile(lab/'IdleBuild.cs',project/'Assets/MGFR/Editor/IdleBuild.cs')
patch=[]
baseline={}
for p,s in changes.items():
    original=read(p) if (main/p).exists() else ''
    patch.extend(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix()))
    if (main/p).exists():baseline[str(main/p)]=hashlib.sha256((main/p).read_bytes()).hexdigest()
with (lab/'changes.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
with (lab/'baseline-hashes.json').open('x',encoding='utf-8') as f:json.dump(baseline,f,indent=2)
with (lab/'desktop-no-runtime.json').open('x',encoding='ascii') as f:f.write('{}\n')
print(project)
