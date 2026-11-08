"""Activate the verified module in the existing launcher target with scoped backups."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLAYER = HERE / 'Player'
MODULE = PLAYER / 'MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'
ENTRY_SOURCE = HERE / 'Source/NativeAvatarActions-main.cs'
INSTALL = 'public static void Install(){MGFR.Repairs.MrClothCoverageRepair.Install();'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def create(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)

def activate(candidate, review):
    candidate = candidate.resolve(strict=True)
    if candidate.parent != HERE / 'MenuBuild' or not candidate.name.startswith('Preview-v'):
        raise ValueError('Candidate outside the explicit menu build directory')
    result = json.loads(review.resolve(strict=True).read_text(encoding='utf-8-sig'))
    if not result['pass'] or not all(item['pass'] for item in result['checks']):
        raise ValueError('Review did not pass')
    compiled = candidate / 'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'
    receipt = json.loads((candidate / 'receipt.json').read_text(encoding='utf-8'))
    if sha(compiled) != receipt['moduleSha256']:
        raise ValueError('Candidate module changed after compilation')
    current = ENTRY_SOURCE.read_text(encoding='utf-8')
    if current.count(INSTALL) != 1 or 'GesturePanelRuntime.Install();' in current:
        raise ValueError('Unexpected current source hook')
    expected = current.replace(INSTALL, INSTALL + 'MGFR.GesturePanel.GesturePanelRuntime.Install();')
    for source in (HERE / 'Source').rglob('*.cs'):
        staged = candidate / 'Source' / source.relative_to(HERE / 'Source')
        if not staged.is_file():
            raise ValueError('Candidate missing source ' + str(source))
        if source == ENTRY_SOURCE:
            if staged.read_text(encoding='utf-8') != expected:
                raise ValueError('Candidate source hook mismatch')
        elif source.read_text(encoding='utf-8') != staged.read_text(encoding='utf-8'):
            raise ValueError('Source changed after candidate compilation: ' + str(source))
    bundle = PLAYER / 'MGFR_Data/StreamingAssets/gesture-touch-panel-v1'
    if bundle.exists():
        raise ValueError('New bundle unexpectedly exists; refusing an unbacked replacement')
    protected = [path for path in PLAYER.rglob('*') if path.is_file() and path != MODULE]
    protected += [ROOT / '启动MGFR.cmd', ROOT / 'DialogueRenderRepair-20261020/launch_final.py']
    protected += list((HERE / 'Voice').rglob('*.py'))
    protected += [ROOT / 'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml']
    before = {str(path): sha(path) for path in protected}
    output = HERE / 'MenuBuild' / ('Activation-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    output.mkdir(parents=True, exist_ok=False)
    targets = [MODULE, ENTRY_SOURCE, ROOT / '项目入口说明.md', ROOT / '测试入口/说明.md']
    backups = []
    for index, target in enumerate(targets):
        backup = output / 'Backups' / (str(index + 1) + '-' + target.name)
        create(backup, target.read_bytes())
        if sha(target) != sha(backup):
            raise ValueError('Backup verification failed')
        backups.append({'target': str(target), 'backup': str(backup), 'beforeSha256': sha(target)})
    create(output / 'before.json', json.dumps({'targets': backups, 'protected': before}, ensure_ascii=False, indent=2).encode('utf-8'))
    print('EXPLICIT_SCOPED_TARGET_COUNT', 2, flush=True)
    print('OVERWRITE', MODULE, flush=True)
    print('OVERWRITE', ENTRY_SOURCE, flush=True)
    print('BACKUP_VERIFIED', output / 'Backups', flush=True)
    create(bundle, (candidate / 'Player/MGFR_Data/StreamingAssets/gesture-touch-panel-v1').read_bytes())
    ENTRY_SOURCE.write_text(expected, encoding='utf-8', newline='')
    MODULE.write_bytes(compiled.read_bytes())
    if sha(MODULE) != sha(compiled) or sha(ENTRY_SOURCE) != sha(candidate / 'Source/NativeAvatarActions-main.cs'):
        raise ValueError('Activation hash mismatch')
    after = {str(path): sha(path) for path in protected}
    if before != after:
        raise ValueError('Protected runtime or voice files changed')
    create(output / 'activated.json', json.dumps({'moduleSha256': sha(MODULE), 'bundleSha256': sha(bundle), 'candidate': str(candidate), 'review': str(review), 'protectedFilesUnchanged': len(protected), 'rootEntryUnchanged': True, 'voiceUnchanged': True}, ensure_ascii=False, indent=2).encode('utf-8'))
    print('CURRENT_RUNTIME_ACTIVATED', output, flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    args = parser.parse_args()
    activate(args.candidate, args.review)
