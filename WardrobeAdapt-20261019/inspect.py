from pathlib import Path
import sys, json
import numpy as np

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'tools/skins'))
from build_swimsuit_v1 import read_base

for skin in ('si-swimsuit-barefoot-ankle-v4', 'si-swimsuit-ready'):
    path = root / 'converted/skins' / skin
    model, a, _ = read_base(path)
    p, _, _, _, _, indices, _, sub = a
    parts = json.loads((path / 'conversion-report.json').read_text(encoding='utf8'))['parts']
    print(skin)
    for part in parts:
        if part['part'] in ('body', 'tail', 'horn', 'bra', 'bottom', 'accessory', 'earrings', 'hair_ribbon', 'tail_accessory'):
            continue
        lo, hi = part['vertexStart'], part['vertexStart'] + part['vertices']
        tri = indices.reshape(-1, 3)
        selected = tri[np.all((tri >= lo) & (tri < hi), axis=1)]
        for side in (-1, 1) if part['part'] in ('sleeves', 'shoes') else (0,):
            t = selected if not side else selected[np.mean(p[selected, 0], axis=1) * side > 0]
            q = p[np.unique(t)]
            print(part['part'], side, 'triangles', len(t), 'bounds', np.round(q.min(0), 4).tolist(), np.round(q.max(0), 4).tolist())
    for i in (13, 15, 21, 22, 23, 25, 26, 27, 32, 35, 58, 61):
        b = model['bones'][i]
        print('bone', i, b['name'], b['positionScaled'])
