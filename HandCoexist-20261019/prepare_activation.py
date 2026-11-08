from pathlib import Path
import ast, difflib, hashlib, json, shutil

lab=Path(__file__).resolve().parent
root=lab.parent
base=root/'ControllerRoom-20261019/Project2'
project=lab/'Project'
coexist=json.loads((lab/'Review/hand-coexist.json').read_text(encoding='utf-8'))
controller=json.loads((lab/'ControllerReview/controller-check.json').read_text(encoding='utf-8'))
assert coexist['pass'] and controller['pass'] and not coexist['headsetTested']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
originals=json.loads((lab/'base-hashes.json').read_text(encoding='utf-8'))
assert all(sha(base/p)==value for p,value in originals.items())
for name in ('Assets/MGFR/Scripts/Character/RoomFloorPlacement.cs','Assets/MGFR/Scripts/Character/ControllerActions.cs',
             'Assets/MGFR/Scripts/Character/ControllerMenuView.cs','Assets/MGFR/Scripts/BareHands/HandDepthMesh.cs',
             'Assets/MGFR/Scripts/BareHands/HandOcclusionEnvelope.cs','Assets/MGFR/Resources/HandDepth.shader',
             'Assets/MGFR/Scripts/Experience/IdleMotionPlayer.cs','Assets/MGFR/Scripts/PhysicsRig/PmxSecondaryPhysics.cs',
             'Assets/MGFR/Scripts/Dialogue/DialogueClient.cs'):
    assert sha(base/name)==sha(project/name),name
patch=[];modified=[]
for p in (project/'Assets/MGFR').rglob('*.cs'):
    rel=p.relative_to(project);before=base/rel
    if before.exists() and sha(before)==sha(p):continue
    modified.append(rel.as_posix())
    old=before.read_text(encoding='utf-8-sig') if before.exists() else ''
    patch+=difflib.unified_diff(old.splitlines(True),p.read_text(encoding='utf-8-sig').splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix())
with (lab/'hand-coexist.patch').open('x',encoding='utf-8') as output:output.writelines(patch)
voice=lab/'VoiceRepair';voice.mkdir()
helper=voice/'launch_unified.py'
source=(root/'ControllerRoom-20261019/VoiceRepair/launch_unified.py').read_text(encoding='utf-8')
source=source.replace("DELIVERY=ROOT/'ControllerRoom-20261019'","DELIVERY=ROOT/'HandCoexist-20261019'")
source=source.replace("PLAYER=DELIVERY/'Project2/Build/Windows/MGFR.exe'","PLAYER=DELIVERY/'Project/Build/Windows/MGFR.exe'")
ast.parse(source)
with helper.open('x',encoding='utf-8') as output:output.write(source)
target=root/'启动MGFR.cmd';backup=lab/'LauncherBackup';backup.mkdir()
saved=backup/'启动MGFR.cmd.bak';assert not saved.exists()
shutil.copyfile(target,saved);assert sha(target)==sha(saved)
candidate=lab/'启动MGFR.cmd.pending'
content='@echo off\r\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -X utf8 "'+str(helper)+'"\r\nif errorlevel 1 pause\r\n'
with candidate.open('xb') as output:output.write(content.encode('ascii'))
assert list(root.glob('启动MGFR*.cmd'))==[target]
player=project/'Build/Windows/MGFR.exe'
receipt={'status':'READY_PENDING_SINGLE_LAUNCHER_OVERWRITE_CONFIRMATION','target':str(target),'overwriteCount':1,
         'backup':str(saved),'candidate':str(candidate),'originalSha256':sha(target),'candidateSha256':sha(candidate),
         'player':str(player),'playerSha256':sha(player),'changedOrAddedSources':modified,
         'nativeAndControllerCheck':coexist,'controllerRegression':controller,'floorAndHandShadersUnchanged':True,
         'headsetVerified':False,'voiceConfigurationUnchanged':True}
with (lab/'delivery-receipt.json').open('x',encoding='utf-8') as output:json.dump(receipt,output,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in receipt.items() if k not in ('nativeAndControllerCheck','controllerRegression','changedOrAddedSources')},ensure_ascii=False,indent=2))
