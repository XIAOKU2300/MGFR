from pathlib import Path
import ast, difflib, hashlib, json, shutil

lab=Path(__file__).resolve().parent
root=lab.parent
project=lab/'Project'
base=root/'Unified-20261019/Project2'
review=json.loads((lab/'Review/floor-placement.json').read_text(encoding='utf-8'))
assert review['pass'] and not review['headsetTested']
assert (project/'Build/Windows/MGFR.exe').is_file()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old_hashes=json.loads((lab/'base-hashes.json').read_text(encoding='utf-8'))
assert all(sha(base/p)==digest for p,digest in old_hashes.items())
changed=[]
preserved=0
patch=[]
for path in (project/'Assets/MGFR').rglob('*.cs'):
    rel=path.relative_to(project)
    original=base/rel
    if original.exists() and sha(original)==sha(path):preserved+=1;continue
    changed.append(rel.as_posix())
    before=original.read_text(encoding='utf-8-sig') if original.exists() else ''
    patch+=difflib.unified_diff(before.splitlines(True),path.read_text(encoding='utf-8-sig').splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix())
assert set(changed)=={
    'Assets/MGFR/Scripts/Character/SiCharacterBootstrap.cs',
    'Assets/MGFR/Scripts/Character/SiCharacterController.cs',
    'Assets/MGFR/Scripts/Character/RoomFloorPlacement.cs',
    'Assets/MGFR/Scripts/Character/RoomFloorReview.cs',
    'Assets/MGFR/Scripts/Dialogue/AutomaticVoiceSession.cs'}
with (lab/'complete-floor-placement.patch').open('x',encoding='utf-8') as output:output.writelines(patch)
for name in ('WardrobeLiveRuntime.cs','ShoeFootPose.cs','WardrobeAdapter.cs'):
    rel=Path('Assets/MGFR/Wardrobe')/name
    assert sha(project/rel)==sha(base/rel)
voice=lab/'VoiceRepair'
voice.mkdir()
source=(root/'Unified-20261019/VoiceRepair/launch_unified.py').read_text(encoding='utf-8')
source=source.replace("DELIVERY=ROOT/'Unified-20261019'","DELIVERY=ROOT/'FloorPlacement-20261019'")
source=source.replace("PLAYER=DELIVERY/'Project2/Build/Windows/MGFR.exe'","PLAYER=DELIVERY/'Project/Build/Windows/MGFR.exe'")
ast.parse(source)
helper=voice/'launch_unified.py'
with helper.open('x',encoding='utf-8') as output:output.write(source)
backup=lab/'LauncherBackup'
backup.mkdir()
target=root/'启动MGFR.cmd'
saved=backup/'启动MGFR.cmd.bak'
assert not saved.exists()
shutil.copyfile(target,saved)
assert sha(saved)==sha(target)
pending=lab/'启动MGFR.cmd.pending'
text='@echo off\r\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -X utf8 "'+str(helper)+'"\r\nif errorlevel 1 pause\r\n'
with pending.open('xb') as output:output.write(text.encode('ascii'))
receipt={'status':'READY_PENDING_ONE_LAUNCHER_OVERWRITE_CONFIRMATION','target':str(target),'overwriteCount':1,'backup':str(saved),'candidate':str(pending),'originalSha256':sha(target),'candidateSha256':sha(pending),'player':str(project/'Build/Windows/MGFR.exe'),'preservedCSharpFiles':preserved,'changedOrAddedSources':changed,'review':review,'headsetVerified':False}
with (lab/'delivery-receipt.json').open('x',encoding='utf-8') as output:json.dump(receipt,output,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in receipt.items() if k!='review'},ensure_ascii=False,indent=2))
