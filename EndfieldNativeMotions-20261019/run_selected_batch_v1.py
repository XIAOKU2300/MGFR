"""Repeat this verified local 16-body + 8-face conversion into a NEW directory.

Requires the retained source extracts in this workspace, Python/numpy/scipy,
and the existing local .NET runtime. Never writes to original game files.
"""
from pathlib import Path
import argparse
import datetime
import json
import time

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New directory inside this work root')
    args = parser.parse_args()
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    out = (args.output or ROOT / 'batch-runs' / stamp).resolve()
    if not out.is_relative_to(ROOT) or out == ROOT:
        parser.error('Output must be a new child directory of ' + str(ROOT))
    if out.exists():
        parser.error('Output already exists; refusing to overwrite: ' + str(out))
    out.mkdir(parents=True, exist_ok=False)

    def expr(path):
        return 'Path(' + repr(str(path)) + ')'

    stages = [
        ('solve_native_body_v2.py', {
            "OUT=ROOT/'body-solved-v2'": 'OUT=' + expr(out / 'body'),
        }),
        ('prepare_native_motion_v3.py', {
            "OUT=ROOT/'motions-v4'": 'OUT=' + expr(out / 'motions-body'),
            "for folder in ['body-solved-v2']:": 'for folder in [' + repr(str(out / 'body')) + ']:',
        }),
        ('bake_native_faces_v2.py', {
            "OUT=ROOT/'motions-v5'": 'OUT=' + expr(out / 'motions'),
            "ROOT/'motions-v4/manifest.json'": expr(out / 'motions-body' / 'manifest.json'),
            "ROOT/'motions-v4'": expr(out / 'motions-body'),
            "ROOT/'motions-v4/A_actor_jsspsi_dialog_state_idle_loop.motion'": expr(out / 'motions-body' / 'A_actor_jsspsi_dialog_state_idle_loop.motion'),
            "ROOT/'face-calibration-v2.json'": expr(out / 'face-calibration.json'),
        }),
        ('export_native_glb_v3.py', {
            "OUT=ROOT/'export-v3'": 'OUT=' + expr(out / 'glb'),
            "ROOT/'motions-v5/manifest.json'": expr(out / 'motions' / 'manifest.json'),
            "ROOT/'motions-v5'": expr(out / 'motions'),
        }),
    ]
    results = []
    for filename, changes in stages:
        source = ROOT / filename
        code = source.read_text(encoding='utf-8')
        for old, new in changes.items():
            if code.count(old) != 1:
                raise RuntimeError('Snapshot contract changed: ' + filename + ' / ' + old)
            code = code.replace(old, new)
        started = time.perf_counter()
        exec(compile(code, str(source), 'exec'), {'__file__': str(source), '__name__': '__main__'})
        results.append({'stage': filename, 'seconds': time.perf_counter() - started})
    manifest = json.loads((out / 'motions/manifest.json').read_text(encoding='utf-8'))
    if len(manifest['clips']) != 24 or manifest.get('errors'):
        raise RuntimeError('Selected batch did not produce all 24 entries')
    with (out / 'batch-report.json').open('x', encoding='utf-8') as f:
        json.dump({'clips': 24, 'output': str(out), 'stages': results}, f, indent=2)
    print('BATCH_COMPLETE', out / 'glb/Si-native-selected.glb')


if __name__ == '__main__':
    main()
