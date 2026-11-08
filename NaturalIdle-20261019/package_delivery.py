from pathlib import Path
import difflib
import hashlib
import json
import shutil

lab=Path(__file__).resolve().parent;root=lab.parent;main=root/'unity-client';project=lab/'Project5'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
changed=[Path(p) for p in ('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs',
 'Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs',
 'Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs',
 'Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs')]
added=[p.relative_to(project) for d in ('Assets/MGFR/Scripts/Experience/NaturalIdle','Assets/MGFR/Skins/ClothPhysics') for p in (project/d).glob('*.cs')]
patch=[];receipt={'project':str(project),'executable':str(project/'Build/Windows/MGFR.exe'),
 'sourceFiles':{},'mainFiles':{},'existingMainModified':False,'review':'Review3/natural-idle-report.json',
 'interactionReview':'InteractionReview/motion-cloth.json','headsetVerified':False}
for rel in changed+added:
    before=(main/rel).read_text(encoding='utf-8-sig') if (main/rel).exists() else ''
    after=(project/rel).read_text(encoding='utf-8-sig')
    patch+=difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix())
    receipt['sourceFiles'][rel.as_posix()]=sha(project/rel)
    if (main/rel).exists():
        backup=lab/'Originals'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
        assert not backup.exists();shutil.copyfile(main/rel,backup)
        receipt['mainFiles'][str(main/rel)]=sha(main/rel)
baseline=json.loads((lab/'baseline-ready.json').read_text(encoding='utf-8'))
assert all(sha(Path(p))==value for p,value in baseline.items())
receipt['executableSha256']=sha(project/'Build/Windows/MGFR.exe')
assert json.loads((lab/receipt['review']).read_text())['pass']
assert json.loads((lab/receipt['interactionReview']).read_text())['pass']
with (lab/'natural-idle-and-physics.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
with (lab/'delivery-receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2,ensure_ascii=False)

for desktop in (False,True):
    name='启动MGFR自然待机版'+('（桌面）' if desktop else '')+'.cmd'
    path=root/name;assert not path.exists()
    lines=['@echo off','setlocal','set "MGFR_NATURAL_IDLE_ROOT=H:\\MGFR\\NaturalIdle-20261019"',
      'set "MGFR_NATURAL_IDLE_LOG=%MGFR_NATURAL_IDLE_ROOT%\\play-%RANDOM%-%RANDOM%-%RANDOM%.log"']
    if desktop:lines.append('set "XR_RUNTIME_JSON=%MGFR_NATURAL_IDLE_ROOT%\\desktop-no-runtime.json"')
    lines.append('echo MGFR Natural Idle: F5 skin, F6 idle, F7 physics, F10 captions, F11 rendering.')
    lines.append('start "" "%MGFR_NATURAL_IDLE_ROOT%\\Project5\\Build\\Windows\\MGFR.exe" '+
      ('-mgfr-noxr ' if desktop else '')+'-mgfr-skins -mgfr-zmd -logFile "%MGFR_NATURAL_IDLE_LOG%"')
    lines.append('endlocal')
    with path.open('x',encoding='ascii',newline='') as f:f.write('\r\n'.join(lines)+'\r\n')
    print(path)
print('Delivery ready; live project hashes unchanged.')
