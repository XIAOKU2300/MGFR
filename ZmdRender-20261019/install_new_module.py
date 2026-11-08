from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone

lab = Path(__file__).resolve().parent
main = lab.parent / 'unity-client'
project = lab / 'Project4'
relative = Path('Assets/MGFR/RenderStyles')
destination = main / relative
launcher = lab.parent / '启动MGFR终末地ZMD渲染版.cmd'
assert not destination.exists(), 'New module target must not exist'
assert not destination.with_suffix('.meta').exists()
assert not launcher.exists()
assert (project / 'Build/Windows/MGFR.exe').is_file()

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

protected = []
for folder in ['Assets/MGFR/Scripts/Rendering', 'Assets/MGFR/Resources',
               'Assets/MGFR/Scripts/BareHands', 'ProjectSettings', 'Packages']:
    protected.extend(p for p in (main / folder).rglob('*') if p.is_file())
before = {str(p): digest(p) for p in protected}
reference = json.loads((lab / 'source-study-manifest.json').read_text(encoding='utf-8'))
for record in reference:
    assert digest(Path(record['source'])) == record['sha256']

# Only create a new folder and files. Nothing in the current renderer is replaced.
shutil.copytree(project / relative, destination)
with destination.with_suffix('.meta').open('xb') as stream:
    stream.write((project / relative.with_suffix('.meta')).read_bytes())

with launcher.open('x', encoding='ascii', newline='') as stream:
    stream.write('@echo off\r\nsetlocal\r\n'
                 'set "MGFR_ZMD_ROOT=H:\\MGFR\\ZmdRender-20261019"\r\n'
                 'set "MGFR_ZMD_LOG=%MGFR_ZMD_ROOT%\\headset-%RANDOM%-%RANDOM%-%RANDOM%.log"\r\n'
                 'echo MGFR ZMD Endfield style - F11 switches ZMD / preserved current rendering\r\n'
                 'echo Log: %MGFR_ZMD_LOG%\r\n'
                 'start "" "%MGFR_ZMD_ROOT%\\Project4\\Build\\Windows\\MGFR.exe" -mgfr-zmd -logFile "%MGFR_ZMD_LOG%"\r\n'
                 'endlocal\r\n')

assert all(digest(Path(path)) == sha for path, sha in before.items())
installed = [p for p in destination.rglob('*') if p.is_file()]
assert all(digest(p) == digest(project / p.relative_to(main)) for p in installed)

hand = []
for p in (main / 'Assets/MGFR/Scripts/BareHands').glob('*.cs'):
    built = project / p.relative_to(main)
    assert built.is_file() and digest(p) == digest(built), p.name
    hand.append(p.name)

receipt = {
    'installedAtUtc': datetime.now(timezone.utc).isoformat(),
    'newModuleDirectory': str(destination / 'ZmdEndfield'),
    'newLauncher': str(launcher),
    'player': str(project / 'Build/Windows/MGFR.exe'),
    'existingFilesOverwritten': 0,
    'protectedFilesCheckedUnchanged': len(before),
    'sourceReferenceFilesUnchanged': len(reference),
    'handScriptsMatchCurrentMain': hand,
    'installedFiles': [{'path': str(p), 'sha256': digest(p)} for p in installed],
    'protectedFileHashes': before,
    'playerRenderChecks': (lab / 'ReviewPlayer1/render-checks.txt').read_text(),
}
with (lab / 'install-receipt.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
print(json.dumps({k: receipt[k] for k in ['newModuleDirectory', 'newLauncher',
      'existingFilesOverwritten', 'protectedFilesCheckedUnchanged',
      'sourceReferenceFilesUnchanged']}, ensure_ascii=False, indent=2))
