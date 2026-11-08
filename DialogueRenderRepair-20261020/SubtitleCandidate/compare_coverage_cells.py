"""Synthetic alpha-pattern RGB-key coverage vs BT709 YUV420 simulation."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parent
out=root/'CoverageCells-v1';out.mkdir(exist_ok=False)
def simulate(rgb):
    a=rgb.astype(np.float64)/255
    y=.2126*a[:,:,0]+.7152*a[:,:,1]+.0722*a[:,:,2]
    u=(a[:,:,2]-y)/1.8556;v=(a[:,:,0]-y)/1.5748
    def chroma(c):
        q=c.reshape(c.shape[0]//2,2,c.shape[1]//2,2).mean(axis=(1,3))
        return (np.round((q+.5)*255)/255-.5).repeat(2,0).repeat(2,1)
    u=chroma(u);v=chroma(v);y=np.round(y*255)/255
    r=y+1.5748*v;b=y+1.8556*u;g=(y-.2126*r-.0722*b)/.7152
    return np.round(np.clip(np.stack([r,g,b],-1),0,1)*255).astype(np.uint8)
yy,xx=np.mgrid[:256,:512]
bayer=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])
alpha_sets={'constant055':np.full(xx.shape,.55),'smoothAlpha':.15+.7*xx/511,'textureAlpha':.5+.35*np.sin(xx*.04)*np.sin(yy*.06)}
reports=[]
for kind,alpha in alpha_sets.items():
    for cell in [1,2,4]:
        coverage=alpha>(bayer[(yy//cell)%4,(xx//cell)%4]+.5)/16
        rgb=np.zeros((*xx.shape,3),dtype=np.uint8);rgb[:,:,1]=255
        rgb[coverage]=[104,165,210]
        yuv=simulate(rgb);a=yuv.astype(np.float64)
        residual=(a[:,:,1]>a[:,:,0]*1.35)&(a[:,:,1]>a[:,:,2]*1.35)&~((a[:,:,0]<5)&(a[:,:,1]>250)&(a[:,:,2]<5))
        report={'alphaPattern':kind,'coverageCellPixels':cell,'totalPixels':int(coverage.size),'residualGreenPixels':int(residual.sum()),'retainedForegroundPixels':int(coverage.sum()),'keyPixelsChanged':int(np.count_nonzero(~coverage & ~np.all(np.abs(yuv.astype(int)-[0,255,0])<5,axis=-1)))}
        reports.append(report)
        if kind=='textureAlpha':
            with (out/f'{kind}-cell{cell}-yuv420.png').open('xb') as f:Image.fromarray(yuv).save(f,format='PNG')
result={'scope':'Synthetic RGB cloth color (104,165,210) over green; BT709 2x2 box chroma subsampling, nearest reconstruction, 8bit quantization. No codec compression, geometry edge, lens warp, scaling, foveation or headset test. Cells align to an even pixel origin.','results':reports}
with (out/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
