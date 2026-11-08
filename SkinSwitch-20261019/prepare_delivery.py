from pathlib import Path
import difflib
import hashlib
import json
import shutil

lab=Path(__file__).resolve().parent
main=lab.parent/'unity-client'
project=lab/'Project8'
candidate=lab/'Candidate'
originals=lab/'Originals'
assert not candidate.exists() and not originals.exists()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
baseline=json.loads((lab/'main-baseline-hashes.json').read_text(encoding='utf-8'))
inputs=json.loads((lab/'input-hashes.json').read_text(encoding='utf-8'))
assert all(sha(Path(path))==value for path,value in baseline.items())
assert all(sha(Path(path))==value for path,value in inputs.items())
assert 'pass=True' in (lab/'ReviewPlayer9/skin-checks.txt').read_text()
assert 'pass=True' in (lab/'ReviewLive10/skin-live-checks.txt').read_text()
assert '[Skin build] Succeeded errors=0' in (lab/'build10.log').read_text(encoding='utf-8')

diff=[]
overwrites=[]
for path,expected in baseline.items():
    target=Path(path);relative=target.relative_to(main)
    backup=originals/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(target,backup)
    assert sha(backup)==expected
    new=candidate/relative;new.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(project/relative,new)
    diff.extend(difflib.unified_diff(target.read_text(encoding='utf-8-sig').splitlines(True),
        new.read_text(encoding='utf-8-sig').splitlines(True),fromfile='a/'+relative.as_posix(),tofile='b/'+relative.as_posix()))
    overwrites.append({'path':path,'beforeSha256':expected,'afterSha256':sha(new),'backup':str(backup)})

for relative in [Path('Assets/MGFR/Skins'),Path('Assets/StreamingAssets/skins')]:
    assert not (main/relative).exists()
    shutil.copytree(project/relative,candidate/relative)
    meta=relative.with_suffix('.meta')
    shutil.copyfile(project/meta,candidate/meta)

with (lab/'changes.patch').open('x',encoding='utf-8') as stream:stream.writelines(diff)
for label,desktop in [('启动MGFR泳装换肤版.cmd',False),('启动MGFR泳装换肤版（桌面）.cmd',True)]:
    launcher=lab.parent/label
    assert not launcher.exists()
    lines=['@echo off','setlocal','set "MGFR_SKINS_ROOT=H:\\MGFR\\SkinSwitch-20261019"',
        'set "MGFR_SKINS_LOG=%MGFR_SKINS_ROOT%\\headset-%RANDOM%-%RANDOM%-%RANDOM%.log"',
        'echo MGFR: F5 skin selection, F11 render style. New outfit: barefoot swimsuit v4.',
        'echo Log: %MGFR_SKINS_LOG%']
    if desktop:lines.append('set "XR_RUNTIME_JSON=%MGFR_SKINS_ROOT%\\desktop-no-runtime.json"')
    flags=' -mgfr-noxr' if desktop else ''
    lines.append('start "" "%MGFR_SKINS_ROOT%\\Project8\\Build9\\Windows\\MGFR.exe" -mgfr-zmd -mgfr-skins -mgfr-skin swimsuit'+flags+' -logFile "%MGFR_SKINS_LOG%"')
    lines.append('endlocal')
    with launcher.open('x',encoding='ascii',newline='') as stream:stream.write('\r\n'.join(lines)+'\r\n')

new_files=[p for p in candidate.rglob('*') if p.is_file() and str(main/p.relative_to(candidate)) not in baseline]
receipt={'state':'standalone_delivered_main_overwrites_await_explicit_approval',
    'mainExistingFilesOverwritten':0,'plannedOverwrites':overwrites,
    'plannedNewFileCount':len(new_files),'inputFilesVerifiedUnchanged':len(inputs),
    'player':str(project/'Build9/Windows/MGFR.exe'),
    'functionalReport':str(lab/'ReviewPlayer9/skin-checks.txt'),
    'liveReport':str(lab/'ReviewLive10/skin-live-checks.txt'),
    'newFiles':[{'path':str(main/p.relative_to(candidate)),'sha256':sha(p)} for p in new_files]}
with (lab/'delivery-receipt.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,ensure_ascii=False,indent=2)
print(json.dumps({key:receipt[key] for key in ['state','mainExistingFilesOverwritten','plannedNewFileCount','inputFilesVerifiedUnchanged']},indent=2))
print('Planned overwrite paths:')
for entry in overwrites:print(entry['path'])
