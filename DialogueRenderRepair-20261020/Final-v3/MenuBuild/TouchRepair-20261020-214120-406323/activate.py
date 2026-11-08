"""Replace only the current runtime module after source/review/backup checks."""
from pathlib import Path
import argparse
import hashlib
import json

SESSION = Path(__file__).resolve().parent
BASE = SESSION.parents[1]
MODULE = BASE / 'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main(candidate_name, result_path):
    if not candidate_name.startswith('Preview-v') or not candidate_name[9:].isdigit():
        raise ValueError('Explicit candidate name required')
    candidate = BASE / 'MenuBuild' / candidate_name
    before = json.loads((SESSION / 'before.json').read_text(encoding='utf-8'))
    module_record = next(item for item in before['targets'] if item['path'] == str(MODULE))
    if sha(MODULE) != module_record['sha256'] or sha(Path(module_record['backup'])) != module_record['sha256']:
        raise RuntimeError('Active module changed or backup differs; no replacement performed')
    result = json.loads(result_path.read_text(encoding='utf-8-sig'))
    if not result['pass'] or not all(item['pass'] for item in result['checks']):
        raise RuntimeError('Candidate review failed')
    sources = list((BASE / 'Source').rglob('*.cs'))
    if len(sources) != len(list((candidate / 'Source').rglob('*.cs'))):
        raise RuntimeError('Source count changed')
    for path in sources:
        copy = candidate / 'Source' / path.relative_to(BASE / 'Source')
        if path.read_text(encoding='utf-8') != copy.read_text(encoding='utf-8'):
            raise RuntimeError('Source changed since compile: ' + str(path))
    for path, digest in before['protected'].items():
        if sha(Path(path)) != digest:
            raise RuntimeError('Protected launcher, voice or data changed: ' + path)
    compiled = candidate / 'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'
    receipt = json.loads((candidate / 'receipt.json').read_text(encoding='utf-8'))
    if sha(compiled) != receipt['moduleSha256']:
        raise RuntimeError('Compiled module mismatch')
    with MODULE.open('wb') as stream:
        stream.write(compiled.read_bytes())
    if sha(MODULE) != sha(compiled):
        raise RuntimeError('Post-copy hash mismatch')
    record = {'module': str(MODULE), 'sha256': sha(MODULE), 'candidate': str(candidate),
              'review': str(result_path), 'checks': len(result['checks']), 'pass': True,
              'protectedFilesUnchanged': len(before['protected']), 'scope': 'Current module only; launch, voice, memory, XR and shaders preserved'}
    with (SESSION / 'activated.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    print(json.dumps(record, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    main(args.candidate, args.result.resolve(strict=True))
