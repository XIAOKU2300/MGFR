"""Actual cloth screenshots and a bounded 4:2:0 chroma sampling simulation."""
from pathlib import Path
import json
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'render-20261020-160733-567074/Results'
OUT=HERE/'cloth-pixel-check'
OUT.mkdir(exist_ok=False)

def rgb420(rgb):
    data=rgb.astype(np.float64)/255
    r,g,b=data[:,:,0],data[:,:,1],data[:,:,2]
    y=.2126*r+.7152*g+.0722*b
    cb=(b-y)/1.8556
    cr=(r-y)/1.5748
    def sample(channel):
        small=channel.reshape(channel.shape[0]//2,2,channel.shape[1]//2,2).mean(axis=(1,3))
        return np.repeat(np.repeat(small,2,axis=0),2,axis=1)
    cb,cr=sample(cb),sample(cr)
    rr=y+1.5748*cr
    bb=y+1.8556*cb
    gg=(y-.2126*rr-.0722*bb)/.7152
    return np.clip(np.rint(np.stack([rr,gg,bb],axis=2)*255),0,255).astype(np.uint8)

def check(rgb):
    data=rgb.astype(np.int32)
    distance=np.sqrt(np.sum((data-np.array([0,255,0]))**2,axis=2))
    green=(data[:,:,1]-np.maximum(data[:,:,0],data[:,:,2])>20)&(distance>85)
    return {'residualGreenPixels':int(green.sum()),'retainedPixels':int((distance>85).sum())}

rows=[]
for style in ['zmd','current']:
    row={'style':style}
    for variant in ['before','after']:
        path=SOURCE/f'swimsuit-{style}-cloth-{variant}.png'
        rgb=np.array(Image.open(path).convert('RGB'))
        row[variant]=check(rgb)
        encoded=rgb420(rgb)
        row[variant+'420Simulation']=check(encoded)
        # A real screenshot composed with the simulated key, saved only for inspection.
        data=encoded.astype(np.int32)
        distance=np.sqrt(np.sum((data-np.array([0,255,0]))**2,axis=2))
        keyed=encoded.copy()
        keyed[distance<=85]=[42,44,50]
        Image.fromarray(keyed).save(OUT/f'{style}-{variant}-420-keyed.png')
    rows.append(row)
passed=all(row['after']['residualGreenPixels']==0 and row['after420Simulation']['residualGreenPixels']<row['before420Simulation']['residualGreenPixels']*.1 for row in rows)
report={'pass':passed,'source':'Actual production-avatar cloth, isolated from body. Key distance 85/255; BT709 2x2 box chroma sampling only; no codec, lens warp, resize or headset. Coverage retains discrete spatial transparency, not continuous alpha.','cases':rows}
with (OUT/'result.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report,indent=2))
