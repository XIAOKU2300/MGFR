"""Refine only new candidate files, retaining both earlier candidates."""
from pathlib import Path
import shutil
import difflib
import json
import hashlib

lab=Path(__file__).resolve().parent
old=lab/'Project2';project=lab/'Project3';main=lab.parent/'unity-client'
assert not project.exists()
changes={}
p=Path('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs')
s=(old/p).read_text(encoding='utf-8')
s=s.replace('        float naturalBlend=1;', '''        float naturalBlend=1;
        MGFR.Skins.SiSkinSwitcher wardrobe;''')
s=s.replace('            attention=face; bones=loader.Renderer.bones;BindClient();',
'''            attention=face; bones=loader.Renderer.bones;BindClient();
            wardrobe=FindAnyObjectByType<MGFR.Skins.SiSkinSwitcher>();''')
s=s.replace('''                bones[index].localPosition=rest[index]+position;bones[index].localRotation=rotation;''',
'''                bones[index].localPosition=rest[index]+position;bones[index].localRotation=rotation;
                if(index==14||index==15)
                {
                    float expansion=(Natural.Breath(seconds,index==14?.06f:.13f)-.44f)*naturalBlend*(1-.25f*speech.Weight);
                    // Ribcage expansion, not a whole-character vertical bob.
                    Vector3 amount=index==14?new Vector3(.0025f,.0008f,.004f):new Vector3(.004f,.0012f,.006f);
                    bones[index].localScale=Vector3.one+amount*expansion;
                }''')
s=s.replace('''                if(side*target.x<.33f)
                {
                    target.x=side*.33f;''',
'''                float clearance=Mathf.Lerp(.33f,wardrobe!=null&&wardrobe.CurrentId=="swimsuit"?.19f:.29f,naturalBlend);
                if(side*target.x<clearance)
                {
                    target.x=side*clearance;''')
changes[p]=s

# Limit validation frame pacing so per-frame rotation measurements are above
# quaternion float resolution and correspond to a useful display interval.
p=Path('Assets/MGFR/Scripts/Experience/NaturalIdle/NaturalIdleReview.cs')
s=(old/p).read_text(encoding='utf-8')
s=s.replace('''            var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,"-mgfr-check-dir");''',
'''            Application.targetFrameRate=72;QualitySettings.vSyncCount=0;
            var args=Environment.GetCommandLineArgs();int i=Array.IndexOf(args,"-mgfr-check-dir");''')
s=s.replace('''            if(haveFirst&&dt>.0001f&&dt<.10f''', '''            if(haveFirst&&dt>.0001f&&dt<.10f''')
changes[p]=s

def ignore(directory,names):return [n for n in names if (Path(directory)/n).relative_to(old) in changes]
for folder in ('Assets','Packages','ProjectSettings'):
    shutil.copytree(old/folder,project/folder,ignore=ignore)
for p,s in changes.items():
    with (project/p).open('x',encoding='utf-8',newline='\n') as f:f.write(s)

# Complete reviewable diff against current main; main itself stays read-only.
paths=[Path(p) for p in ('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs',
    'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs','Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs')]
paths+=list(p.relative_to(project) for d in ('Assets/MGFR/Scripts/Experience/NaturalIdle','Assets/MGFR/Skins/ClothPhysics') for p in (project/d).glob('*.cs'))
patch=[];hashes={}
for p in paths:
    before=(main/p).read_text(encoding='utf-8-sig') if (main/p).exists() else ''
    after=(project/p).read_text(encoding='utf-8-sig')
    patch+=difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+p.as_posix(),tofile='b/'+p.as_posix())
    if (main/p).exists():hashes[str(main/p)]=hashlib.sha256((main/p).read_bytes()).hexdigest()
with (lab/'changes-final.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
with (lab/'baseline-final.json').open('x',encoding='utf-8') as f:json.dump(hashes,f,indent=2)
print(project)
