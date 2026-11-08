from pathlib import Path
import ast, difflib, hashlib, json, shutil

lab=Path(__file__).resolve().parent
root=lab.parent
project=lab/'Project2'
base=root/'FloorPlacement-20261019/Project'
unified=root/'Unified-20261019/Project2'
review=json.loads((lab/'Review2/controller-check.json').read_text(encoding='utf-8'))
floor=json.loads((lab/'FloorReview2/floor-placement.json').read_text(encoding='utf-8'))
assert review['pass'] and floor['pass']
assert not review['headsetTested'] and not review['microphoneUsed']
assert not (root.parent/'Controller.tmp').exists()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
before=json.loads((lab/'base-hashes.json').read_text(encoding='utf-8'))
assert all(sha(base/p)==digest for p,digest in before.items())
preserved=0
modified=[]
patch=[]
for p in (project/'Assets/MGFR').rglob('*.cs'):
    rel=p.relative_to(project)
    old=unified/rel
    if old.exists() and sha(old)==sha(p):preserved+=1;continue
    modified.append(rel.as_posix())
    a=old.read_text(encoding='utf-8-sig') if old.exists() else ''
    patch+=difflib.unified_diff(a.splitlines(True),p.read_text(encoding='utf-8-sig').splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix())
for name in ('Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs','Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs',
             'Assets/MGFR/Skins/SiSkinSwitcher.cs','Assets/MGFR/Wardrobe/ShoeFootPose.cs','Assets/MGFR/Wardrobe/WardrobeAdapter.cs',
             'Assets/MGFR/Scripts/Dialogue/DialogueClient.cs'):
    assert sha(project/name)==sha(unified/name),name
with (lab/'combined-floor-controller.patch').open('x',encoding='utf-8') as output:output.writelines(patch)
voice=lab/'VoiceRepair';voice.mkdir()
source=(root/'Unified-20261019/VoiceRepair/launch_unified.py').read_text(encoding='utf-8')
source=source.replace("DELIVERY=ROOT/'Unified-20261019'","DELIVERY=ROOT/'ControllerRoom-20261019'")
ast.parse(source)
helper=voice/'launch_unified.py'
with helper.open('x',encoding='utf-8') as output:output.write(source)
assert (project/'Build/Windows/MGFR.exe').is_file()
backup=lab/'LauncherBackup';backup.mkdir()
target=root/'启动MGFR.cmd';saved=backup/'启动MGFR.cmd.bak'
assert not saved.exists();shutil.copyfile(target,saved);assert sha(saved)==sha(target)
pending=lab/'启动MGFR.cmd.pending'
content='@echo off\r\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -X utf8 "'+str(helper)+'"\r\nif errorlevel 1 pause\r\n'
with pending.open('xb') as output:output.write(content.encode('ascii'))
launchers=list(root.glob('启动MGFR*.cmd'));assert launchers==[target]
receipt={'status':'READY_PENDING_ONE_LAUNCHER_OVERWRITE_CONFIRMATION','target':str(target),'overwriteCount':1,
         'backup':str(saved),'candidate':str(pending),'originalSha256':sha(target),'candidateSha256':sha(pending),
         'player':str(project/'Build/Windows/MGFR.exe'),'playerSha256':sha(project/'Build/Windows/MGFR.exe'),
         'unifiedSourceFilesPreserved':preserved,'modifiedOrAddedSources':modified,'controllerCheck':review,'floorCheck':floor,
         'headsetVerified':False,'voiceServiceConfigurationChanged':False,'onlyOneRootLauncher':True}
with (lab/'delivery-receipt.json').open('x',encoding='utf-8') as output:json.dump(receipt,output,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in receipt.items() if k not in ('controllerCheck','floorCheck','modifiedOrAddedSources')},ensure_ascii=False,indent=2))
