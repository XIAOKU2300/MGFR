"""BT.709 YUV420 chroma subsampling simulation, not codec/headset verification."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent
out=root/'Yuv420Probe-v1'
out.mkdir(exist_ok=False)
def simulate(rgb):
    a=np.asarray(rgb,dtype=np.float64)/255
    y=.2126*a[:,:,0]+.7152*a[:,:,1]+.0722*a[:,:,2]
    u=(a[:,:,2]-y)/1.8556
    v=(a[:,:,0]-y)/1.5748
    def downup(c):
        # 2x2 box chroma downsample with nearest reconstruction, then 8-bit quantization.
        low=c.reshape(c.shape[0]//2,2,c.shape[1]//2,2).mean(axis=(1,3))
        low=np.round((low+.5)*255)/255-.5
        return low.repeat(2,axis=0).repeat(2,axis=1)
    u=downup(u);v=downup(v);y=np.round(y*255)/255
    r=y+1.5748*v;b=y+1.8556*u;g=(y-.2126*r-.0722*b)/.7152
    return np.round(np.clip(np.stack([r,g,b],axis=-1),0,1)*255).astype(np.uint8)
reports=[]
for version,label in [('v1','fine-dither'),('v2','neutral-opaque-panel')]:
    before=np.asarray(Image.open(root/f'PixelProbe-{version}/04-repaired-green.png').convert('RGB'))
    after=simulate(before)
    with (out/f'{label}-yuv420.png').open('xb') as f:Image.fromarray(after).save(f,format='PNG')
    foreground=~np.all(before==[0,255,0],axis=-1)
    ys,xs=np.where(foreground)
    # 4-pixel inset excludes the unavoidable panel/surrounding real-room silhouette.
    roi=np.zeros(foreground.shape,dtype=bool);roi[ys.min()+4:ys.max()-3,xs.min()+4:xs.max()-3]=True
    a=after.astype(np.float64)
    contaminated=(a[:,:,1]>a[:,:,0]*1.35)&(a[:,:,1]>a[:,:,2]*1.35)
    exactkey=(a[:,:,0]<5)&(a[:,:,1]>250)&(a[:,:,2]<5)
    residual=contaminated&~exactkey
    reports.append({'method':label,'interiorResidualGreenPixels':int(np.count_nonzero(residual&roi)),'interiorPixels':int(np.count_nonzero(roi)),'allResidualGreenPixels':int(np.count_nonzero(residual))})
result={'pass':reports[1]['interiorResidualGreenPixels']==0 and reports[0]['interiorResidualGreenPixels']>1000,'scope':'BT709 RGB->YUV420 2x2 box chroma subsampling, nearest reconstruction and 8bit quantization simulation; no codec compression or headset','results':reports}
with (out/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
