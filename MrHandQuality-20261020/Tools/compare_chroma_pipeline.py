"""Offline v20.14.1 shader simulation. This is NOT a capture of ALVR/headset output."""
import argparse,json,subprocess,io
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def mask(rgb,threshold=85,feather=.05,hsv=False,stock_hsv=False):
 if hsv:
  # Intended HSV algorithm, separately labelled: stock v20.14.1 sets mode=2 but
  # its shader tests mode==3 before conversion. Do not recommend enabling it.
  if not stock_hsv:
   high=rgb.max(axis=2);low=rgb.min(axis=2);delta=high-low;safe=np.maximum(delta,1e-8)
   hue=np.where(high==rgb[:,:,0],(rgb[:,:,1]-rgb[:,:,2])/safe,np.where(high==rgb[:,:,1],2+(rgb[:,:,2]-rgb[:,:,0])/safe,4+(rgb[:,:,0]-rgb[:,:,1])/safe))/6
   hue=np.where(delta>0,hue%1,0);sat=np.where(high>0,delta/np.maximum(high,1e-8),0);rgb=np.stack([hue,sat,high],axis=2)
  lo=np.array([80/360,.3,.1]);outer=np.array([70/360,.2,0]);hi=np.array([160/360,1,1]);end=np.array([170/360,1.1,1.1])
 else:
  key=np.array([0,1,0]);d=threshold/255;lo=key-d*(1-feather);outer=key-d*(1+feather);hi=key+d*(1-feather);end=key+d*(1+feather)
 return np.maximum(smooth(lo,outer,rgb),smooth(hi,end,rgb)).max(axis=2)
def compose(rgb,a,bg):return np.clip(rgb*a[:,:,None]+np.array(bg)*(1-a[:,:,None]),0,1)
def image(rgb):return Image.fromarray(np.uint8(np.clip(rgb,0,1)*255))
def main():
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--ffmpeg',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False)
 metrics=[]
 for source in sorted(a.input.rglob('*-aa1.png')):
  im=Image.open(source).convert('RGB');rgb=np.asarray(im,dtype=np.float32)/255;name=source.parent.name+'-'+source.stem
  encoded=a.output/(name+'.mp4');decoded=a.output/(name+'-decoded.png')
  cmd=[str(a.ffmpeg),'-v','error','-n','-loop','1','-i',str(source),'-t','0.1','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','1',str(encoded)]
  subprocess.run(cmd,check=True);subprocess.run([str(a.ffmpeg),'-v','error','-n','-i',str(encoded),'-frames:v','1',str(decoded)],check=True)
  post=np.asarray(Image.open(decoded).convert('RGB'),dtype=np.float32)/255
  for stage,data in [('raw',rgb),('h264-420-crf18',post)]:
   alpha=mask(data);comp=compose(data,alpha,[.17,.19,.22]);image(comp).save(a.output/(name+'-'+stage+'-composite.png'))
   # Green excess is diagnostic only: intentional green/cyan pixels are protected,
   # not counted as proof of improvement or deleted to improve a score.
   foreground=(np.max(np.abs(rgb-np.array([0,1,0])),axis=2)>.03)
   edge=np.array(Image.fromarray(np.uint8(foreground)*255).filter(ImageFilter.MaxFilter(5))) != np.array(Image.fromarray(np.uint8(foreground)*255).filter(ImageFilter.MinFilter(5)))
   entry={'image':name,'stage':stage,'partialAlphaPixels':int(((alpha>0)&(alpha<1)).sum()),'edgeGreenExcessMean':float(np.maximum(data[:,:,1]-np.maximum(data[:,:,0],data[:,:,2]),0)[edge].mean()) if edge.any() else 0,'rgbCandidates':{}}
   for threshold in [70,85,100]:
    m=mask(data,threshold);entry['rgbCandidates'][str(threshold)]={'foregroundCoverage':float(m[foreground].mean())}
   entry['stockHsvMode2ForegroundCoverage']=float(mask(data,hsv=True,stock_hsv=True)[foreground].mean())
   entry['intendedHsvMode3ForegroundCoverage']=float(mask(data,hsv=True)[foreground].mean())
   metrics.append(entry)
  w,h=im.size;crop=(int(w*.25),int(h*.15),int(w*.75),int(h*.65));im.crop(crop).resize((900,1200)).save(a.output/(name+'-detail.png'))
 summary={'source':'OFFLINE_SIMULATION_NOT_ALVR_HEADSET','encoding':'libx264 fast CRF18 8-bit yuv420p 30fps; not NVENC 30Mbps','rgbKey':[0,255,0],'threshold':85,'feather':.05,'colorConversion':'identity; no unmeasured gamma/SGSR assumed','hsvCaveat':'v20.14.1 Rust sets HSV mode 2 while WGSL checks 3; HSV enablement is not recommended without device validation','recommendation':'Keep current RGB 85 / .05 initially. Candidate thresholds are offline comparisons only. Rollback means retain saved installation settings; tool never writes them.','metrics':metrics}
 with (a.output/'comparison.json').open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2)
 print('offline comparisons',len(metrics))
if __name__=='__main__':main()
