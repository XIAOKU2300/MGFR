from pathlib import Path
import hashlib,json,difflib

lab=Path(__file__).resolve().parent;root=lab.parent;base=root/'ShoeEasy-20261019/Project';project=lab/'Project2'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
motion=json.loads((lab/'ReviewMotion2/unified-motion.json').read_text(encoding='utf-8'))
shoe=(lab/'ReviewShoes2/result.txt').read_text(encoding='utf-8');wardrobe=(lab/'ReviewWardrobe/result.txt').read_text(encoding='utf-8')
assert motion['pass'] and 'pass=True' in shoe and 'pass=True' in wardrobe
baseline=json.loads((lab/'base-hashes.json').read_text(encoding='utf-8'))
assert all(sha(Path(p))==digest for p,digest in baseline.items())
cleanup=json.loads((lab/'launcher-cleanup.json').read_text(encoding='utf-8'))
assert all(sha(Path(p['path']))==p['sha256'] and sha(Path(p['backup']))==p['sha256'] for p in cleanup['targets'])

patch=[];modified={};preserved={}
for p in (project/'Assets/MGFR').rglob('*.cs'):
    rel=p.relative_to(project);before=base/rel
    if before.exists() and sha(before)==sha(p):preserved[rel.as_posix()]=sha(p);continue
    modified[rel.as_posix()]=sha(p)
    a=before.read_text(encoding='utf-8-sig') if before.exists() else '';b=p.read_text(encoding='utf-8-sig')
    patch+=difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix())
with (lab/'complete-integration.patch').open('x',encoding='utf-8') as f:f.writelines(patch)
receipt={'featureBase':str(base),'project':str(project),'executable':str(project/'Build/Windows/MGFR.exe'),
 'executableSha256':sha(project/'Build/Windows/MGFR.exe'),'modifiedSources':modified,'preservedSources':preserved,
 'wardrobeSourceIdentical':all(p.read_bytes()==(project/'Assets/MGFR/Wardrobe'/p.name).read_bytes() for p in (base/'Assets/MGFR/Wardrobe').glob('*.cs')),
 'motionReview':motion,'shoeReplayPass':True,'wardrobeReplayPass':True,'headsetVerified':False,
 'oldLauncherCount':cleanup['count'],'oldLauncherDeletion':'AWAITING_USER_CONFIRMATION'}
with (lab/'delivery-receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2,ensure_ascii=False)
launcher=root/'启动MGFR.cmd';assert not launcher.exists()
lines=['@echo off','setlocal','set "MGFR_UNIFIED_ROOT=H:\\MGFR\\Unified-20261019"',
 'set "MGFR_UNIFIED_LOG=%MGFR_UNIFIED_ROOT%\\headset-%RANDOM%-%RANDOM%-%RANDOM%.log"',
 'echo MGFR Unified - full wardrobe, easy shoes, natural idle and soft hair.',
 'echo F5 skin; F6 idle; F7 physics; F12 wardrobe; Shift+F12 restore.',
 'start "" "%MGFR_UNIFIED_ROOT%\\Project2\\Build\\Windows\\MGFR.exe" -mgfr-skins -mgfr-skin swimsuit -mgfr-zmd -mgfr-mr-clean-edge -mgfr-wardrobe -mgfr-shoes -logFile "%MGFR_UNIFIED_LOG%"','endlocal']
with launcher.open('x',encoding='ascii',newline='') as f:f.write('\r\n'.join(lines)+'\r\n')
print(launcher)
print('Complete feature base verified; all three checks passed.')
print('33 old launchers remain pending the required confirmation; all backed up.')
