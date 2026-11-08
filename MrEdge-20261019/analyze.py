"""Desktop RGB-key simulation, using ALVR v20.14.1's channel-box smoothstep mask.

This excludes video encoding, reprojection and the headset compositor.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw

lab = Path(__file__).resolve().parent
out = lab / 'Review'

def smoothstep(lo, hi, value):
    t = np.clip((value - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)

def mask(rgb):
    key = np.array([0., 1., 0.], dtype=np.float32)
    threshold, feather = 85 / 255, .05
    d = np.abs(rgb - key)
    return smoothstep(threshold * (1 - feather), threshold * (1 + feather), d).max(axis=-1)

def dilate(m, radius=2):
    p = np.pad(m, radius)
    h, w = m.shape
    result = m.copy()
    for y in range(2 * radius + 1):
        for x in range(2 * radius + 1):
            result |= p[y:y + h, x:x + w]
    return result

def composite(rgb):
    a = mask(rgb)[..., None]
    return np.uint8(np.clip((rgb * a + np.array([.16, .17, .19]) * (1 - a)) * 255, 0, 255))

assert mask(np.array([0., 1., 0.])) == 0
assert mask(np.array([1., 1., 1.])) == 1
report = {'source': 'ACTUAL_UNITY_RENDER_WITH_SIMULATED_ALVR_RGB_KEY_NOT_HEADSET',
          'alvr': {'version': '20.14.1', 'distance_threshold': 85, 'feathering': .05}, 'views': {}}
for view in ('fullbody', 'face', 'threequarter'):
    arrays = [np.asarray(Image.open(out / f'{view}-{v}.png').convert('RGB'), dtype=np.float32) / 255
              for v in ('before', 'after')]
    before, after = arrays
    # Fixed region around the after image's true green background; used for both variants.
    bg = np.max(np.abs(after - [0, 1, 0]), axis=-1) < .005
    band = dilate(bg, 2) & ~bg
    band |= dilate(~bg, 2) & bg
    counts = []
    for v, rgb in zip(('before', 'after'), arrays):
        visible = mask(rgb) > .1
        excess = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
        counts.append(int(np.count_nonzero(band & visible & (excess > .08))))
        path = out / f'{view}-{v}-key-sim.png'
        assert not path.exists()
        Image.fromarray(composite(rgb)).save(path)
    report['views'][view] = {'visible_green_edge_pixels_before': counts[0], 'after': counts[1],
                              'reduction_percent': round(100 * (1 - counts[1] / max(counts[0], 1)), 2),
                              'pure_green_corner_preserved': bool(bg[0, 0])}
    pair = Image.new('RGB', (1200, 850), '#252830')
    draw = ImageDraw.Draw(pair)
    for i, v in enumerate(('before', 'after')):
        img = Image.open(out / f'{view}-{v}-key-sim.png')
        img.thumbnail((600, 800))
        pair.paste(img, (i * 600, 42))
        draw.text((i * 600 + 20, 15), 'BEFORE: 4x MSAA' if i == 0 else 'AFTER: MR edge guard', fill='white')
    with (out / f'{view}-compare.png').open('xb') as f:
        pair.save(f, format='PNG')
    if view == 'face':
        # Pixel-nearest zoom of the left face/hair silhouette, for honest edge inspection.
        yy, xx = np.nonzero(~bg)
        cy = int(np.median(yy))
        candidates = np.where(~bg[max(0, cy - 40):cy + 40])[1]
        cx = int(candidates.min()) if candidates.size else int(xx.min())
        box = (max(0, cx - 24), cy - 64, cx + 104, cy + 64)
        zoom = Image.new('RGB', (1024, 550), '#252830')
        d = ImageDraw.Draw(zoom)
        for i, v in enumerate(('before', 'after')):
            crop = Image.open(out / f'{view}-{v}-key-sim.png').crop(box).resize((512, 512), Image.Resampling.NEAREST)
            zoom.paste(crop, (i * 512, 38))
            d.text((i * 512 + 15, 12), 'BEFORE - 4x pixel zoom' if i == 0 else 'AFTER - 4x pixel zoom', fill='white')
        with (out / 'face-edge-zoom.png').open('xb') as f:
            zoom.save(f, format='PNG')
with (out / 'edge-metrics.json').open('x', encoding='utf8') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
