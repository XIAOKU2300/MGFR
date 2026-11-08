"""Prepare a new, local MGFR cloth project from an already converted Si v4 skin.

This helper is deliberately profile-bound. It never edits the client or input
skin, builds an executable, starts Unity, or installs into a live project.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]
HANDS = Path('Assets/MGFR/Scripts/BareHands/BareHandInteraction.cs')
MODULE = Path('Assets/MGFR/Skins/ClothPhysics')
BUILD = Path('Assets/MGFR/Editor/SwimsuitClothBuild.cs')
FIELDS_ANCHOR = '  public HandJointSource Source {get;private set;}'
ACQUIRE_ANCHOR = '''  void AcquireHand(int h,bool afterPhysics)
  {
   if(!acquisitionPending[h])return;'''
HUD_ANCHOR = '(GrabbedBody[0]>=0||GrabbedBody[1]>=0?"抓取中":"无")'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def safe_file(root, relative):
    path = (root / relative).resolve()
    path.relative_to(root.resolve())
    if not path.is_file():
        raise ValueError('Required skin file missing: ' + str(relative))
    return path


def preflight(client, skin):
    profile = json.loads((SKILL_ROOT / 'references/si-runtime-profile.json').read_text(encoding='utf-8'))
    data_path = safe_file(skin, 'si_model.json')
    binary = safe_file(skin, 'si_model.bin')
    manifest_path = safe_file(skin, 'skin.json')
    for name, expected in profile['inputHashes'].items():
        if digest(safe_file(skin, name)) != expected:
            raise ValueError('Skin fingerprint differs at ' + name + '; build a new profile instead of bypassing this check.')
    with binary.open('rb') as stream:
        if stream.read(8) != struct.pack('<II', 0x5346474D, 1):
            raise ValueError('Expected MGFR binary v1 header.')
    data = json.loads(data_path.read_text(encoding='utf-8-sig'))
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    for key, expected in profile['counts'].items():
        if data['counts'][key] != expected:
            raise ValueError('Skin count differs at ' + key)
    if signature([(b['name'], b['parent']) for b in data['bones']]) != profile['rigSignature']:
        raise ValueError('Bone names/order/parents differ.')
    if signature([b['name'] for b in data['blendShapes']]) != profile['morphSignature']:
        raise ValueError('Expression names/order differ.')
    for material in data['materials']:
        if material.get('textureFile'):
            safe_file(skin, Path('textures') / material['textureFile'])
    for binding in manifest.get('materialBindings', []):
        for key in ('albedo', 'normalData', 'sourceLightData'):
            if binding.get(key):
                safe_file(skin, binding[key])

    required = {
        'Assets/MGFR/Skins/SiSkinSwitcher.cs': ('CurrentAppearance', 'TrySelect'),
        'Assets/MGFR/Scripts/Character/SiCharacterLoader.cs': ('ReplaceSkinMesh', 'ApplyAppearance'),
        'Assets/MGFR/Skins/ZmdSkinBinding.cs': ('BindAppearance',),
        'Assets/MGFR/Skins/Resources/SiSwimsuitCloth.shader': ('SwimsuitCloth',),
    }
    for relative, markers in required.items():
        path = client / relative
        if not path.is_file():
            raise ValueError('Host rendering/skin API missing: ' + relative + '; complete runtime-integration.md first.')
        text = path.read_text(encoding='utf-8-sig')
        if any(marker not in text for marker in markers):
            raise ValueError('Host API changed: ' + relative)
    if (client / MODULE).exists() or (client / BUILD).exists():
        raise ValueError('Host already contains the cloth module/build entry; inspect the existing integration instead of replacing it.')
    source = (client / HANDS).read_text(encoding='utf-8-sig')
    if 'ExternalClothGrab' in source:
        raise ValueError('Host already declares cloth grab ownership; adapt its current API instead of injecting a duplicate.')
    for anchor in (FIELDS_ANCHOR, ACQUIRE_ANCHOR, HUD_ANCHOR):
        if source.count(anchor) != 1:
            raise ValueError('BareHandInteraction acquisition/HUD API differs; inspect before patching.')
    for folder in ('Assets', 'Packages', 'ProjectSettings'):
        if not (client / folder).is_dir():
            raise ValueError('Missing Unity project folder: ' + folder)
    for name in profile['runtimeSources']:
        if not (SKILL_ROOT / 'scripts/runtime' / name).is_file():
            raise ValueError('Skill runtime template missing: ' + name)
    return profile, source


def prepare(client, skin, out):
    profile, source = preflight(client, skin)
    if out.exists():
        raise ValueError('Output already exists; choose a fresh folder.')
    if out == client or client in out.parents or out == skin or skin in out.parents:
        raise ValueError('Output must be separate from the client and input skin directories.')
    target_skin = Path('Assets/StreamingAssets/skins') / profile['skinId']
    excluded = {HANDS, target_skin}

    def ignore(directory, names):
        return [name for name in names if (Path(directory) / name).relative_to(client) in excluded]

    out.mkdir(parents=True)
    for folder in ('Assets', 'Packages', 'ProjectSettings'):
        shutil.copytree(client / folder, out / folder, ignore=ignore)
    source = source.replace(FIELDS_ANCHOR, FIELDS_ANCHOR + '\n  public Func<int,bool> ExternalClothGrab;')
    source = source.replace(ACQUIRE_ANCHOR, '''  void AcquireHand(int h,bool afterPhysics)
  {
   if(ExternalClothGrab!=null&&ExternalClothGrab(h))
   {Release(h);blockedUntilOpen[h]=true;GrabStatus[h]="泳装布料抓取中";return;}
   if(!acquisitionPending[h])return;''')
    source = source.replace(HUD_ANCHOR,
        '(GrabbedBody[0]>=0||GrabbedBody[1]>=0||(ExternalClothGrab!=null&&(ExternalClothGrab(0)||ExternalClothGrab(1)))?"抓取中":"无")')
    with (out / HANDS).open('x', encoding='utf-8') as stream:
        stream.write(source)

    module = out / MODULE
    module.mkdir()
    for name in profile['runtimeSources']:
        destination = out / BUILD if name == BUILD.name else module / name
        with destination.open('xb') as stream:
            stream.write((SKILL_ROOT / 'scripts/runtime' / name).read_bytes())
    skin_out = out / target_skin
    skin_out.mkdir(parents=True)
    for name in ('si_model.json', 'si_model.bin', 'skin.json'):
        with (skin_out / name).open('xb') as stream:
            stream.write((skin / name).read_bytes())
    shutil.copytree(skin / 'textures', skin_out / 'textures')
    with (skin_out / '.gitignore').open('x', encoding='ascii') as stream:
        stream.write('*\n!.gitignore\n')
    record = {'client': str(client), 'inputSkin': str(skin), 'output': str(out),
        'originalFilesModified': 0, 'profile': profile['id'],
        'inputHashes': {name: digest(skin / name) for name in profile['inputHashes']},
        'hostHandSourceHash': digest(client / HANDS), 'candidateHandSourceHash': digest(out / HANDS),
        'next': 'Compile with SwimsuitClothBuild.Build; optionally run one -mgfr-cloth-check smoke test.'}
    with (out / 'cloth-preparation.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--skin', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--inspect', action='store_true', help='Read-only compatibility check; no project is generated.')
    args = parser.parse_args()
    client, skin = args.client.resolve(), args.skin.resolve()
    if args.inspect:
        profile, _ = preflight(client, skin)
        print(json.dumps({'compatible': True, 'profile': profile['id'], 'counts': profile['counts'],
                          'writes': 0}, ensure_ascii=False, indent=2))
    else:
        if args.out is None:
            parser.error('--out is required unless --inspect is used')
        result = prepare(client, skin, args.out.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print('Cannot prepare cloth candidate: ' + str(error), file=sys.stderr)
        sys.exit(2)
