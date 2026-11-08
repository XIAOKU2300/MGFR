"""Refine and reshape the ankle surface, keeping toes, soles and upper calf fixed."""
from pathlib import Path
import argparse,json,struct
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.sparse import coo_matrix
from build_swimsuit_v1 import read_base,emit_json

ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
assert not args.out.exists()
m,arrays,morphs=read_base(args.input);p,n,u,bi,bw,ix,bind,sub=arrays
r=json.loads((args.input/'conversion-report.json').read_text(encoding='utf-8'));part=next(x for x in r['parts'] if x['part']=='body')
old_n=len(p);body_end=part['vertexStart']+part['vertices']
positions=list(p);uvs=list(u);indices=list(bi);weights=list(bw)
tri=ix[sub[7,0]:sub[7,0]+sub[7,1]].reshape(-1,3).copy()

def midpoint(a,b,cache):
    key=tuple(sorted((int(a),int(b))))
    if key in cache:return cache[key]
    j=len(positions);cache[key]=j
    positions.append((positions[a]+positions[b])*.5);uvs.append((uvs[a]+uvs[b])*.5)
    vote={}
    for v in (a,b):
        for bone,w in zip(indices[v],weights[v]):vote[int(bone)]=vote.get(int(bone),0)+float(w)*.5
    ranked=sorted(vote,key=vote.get,reverse=True)[:4];w=np.array([vote[k] for k in ranked]);w/=w.sum()
    indices.append(np.array(ranked,dtype='<u2'));weights.append(w.astype('<f4'))
    return j

for level in range(2):
    xyz=np.asarray(positions);cache={};out=[]
    for A,B,C in tri:
        vs=xyz[[A,B,C]];mid=(vs+np.roll(vs,-1,axis=0))*.5
        mark=(mid[:,1]>.032)&(mid[:,1]<.20)&(mid[:,2]>-.10)
        e=[midpoint(int(v),int(w),cache) if on else -1 for v,w,on in zip((A,B,C),(B,C,A),mark)]
        ab,bc,ca=e;k=int(mark.sum())
        if k==0:out.append((A,B,C))
        elif k==3:out.extend(((A,ab,ca),(ab,B,bc),(ca,bc,C),(ab,bc,ca)))
        elif k==1:
            if ab>=0:out.extend(((A,ab,C),(ab,B,C)))
            elif bc>=0:out.extend(((B,bc,A),(bc,C,A)))
            else:out.extend(((C,ca,B),(ca,A,B)))
        else:
            if ca<0:out.extend(((B,bc,ab),(A,ab,bc),(A,bc,C)))
            elif ab<0:out.extend(((C,ca,bc),(B,bc,ca),(B,ca,A)))
            else:out.extend(((A,ab,ca),(C,ca,ab),(C,ab,B)))
    tri=np.array(out,dtype='<u4')

p=np.array(positions,dtype=float);u=np.array(uvs,dtype='<f4');bi=np.array(indices,dtype='<u2');bw=np.array(weights,dtype='<f4')
before=p.copy();body=np.unique(tri);edges=np.unique(np.sort(np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]])),axis=1),axis=0)
profiles=[]
def smoothstep(t):t=np.clip(t,0,1);return t*t*(3-2*t)
for side in (1,-1):
    foot_edges=edges[(p[edges].mean(1)[:,0]*side>0)&(p[edges].min(1)[:,1]<.23)]
    def section(y):
        a=p[foot_edges[:,0]];b=p[foot_edges[:,1]];mask=((a[:,1]<=y)&(b[:,1]>=y))|((b[:,1]<=y)&(a[:,1]>=y))
        a=a[mask];b=b[mask];valid=np.abs(a[:,1]-b[:,1])>1e-8;a=a[valid];b=b[valid]
        t=(y-a[:,1])/(b[:,1]-a[:,1]);z=a[:,2]+t*(b[:,2]-a[:,2]);return float(z.min()),float(z.max())
    levels=np.linspace(.036,.195,100);bounds=np.array([section(y) for y in levels]);front=PchipInterpolator(levels,bounds[:,0]);back=PchipInterpolator(levels,bounds[:,1])
    y0,y1=.045,.155;f0,f1=float(front(y0)),float(front(y1))
    target_back=PchipInterpolator([.036,.05,.075,.10,.135,.195],[float(back(.036)),float(back(.05)),.0335,.0335,float(back(.135)),float(back(.195))])
    ids=body[(p[body,0]*side>0)&(p[body,1]>.036)&(p[body,1]<.195)]
    y=p[ids,1];z=p[ids,2];oldfront=front(y);oldback=back(y)
    t=np.clip((y-y0)/(y1-y0),0,1);desired_front=f1+(f0-f1)*(1-t)**3.8
    blend=smoothstep((y-.04)/.018)*(1-smoothstep((y-.135)/.045))
    newfront=oldfront+(desired_front-oldfront)*blend
    newback=oldback  # Keep the original posterior contour; avoid an over-pinched Achilles notch.
    fraction=np.clip((z-oldfront)/(oldback-oldfront),0,1)
    p[ids,2]=newfront+(newback-newfront)*fraction
    profiles.append(dict(side=side,frontAnchors=[f0,f1],regionY=[.036,.195]))

# Gentle geometric fairing after local refinement. Duplicate UV seam vertices move together.
_,inv=np.unique(np.round(p[body]*1e6).astype(np.int64),axis=0,return_inverse=True)
count=inv.max()+1;unique=np.zeros((count,3));np.add.at(unique,inv,p[body]);unique/=np.bincount(inv)[:,None]
lookup=np.full(len(p),-1,int);lookup[body]=inv
links=lookup[edges];links=links[links[:,0]!=links[:,1]];links=np.unique(np.sort(links,axis=1),axis=0)
rr=np.r_[links[:,0],links[:,1]];cc=np.r_[links[:,1],links[:,0]]
adj=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(count,count)).tocsr();degree=np.asarray(adj.sum(1)).ravel()
mask=smoothstep((unique[:,1]-.035)/.025)*(1-smoothstep((unique[:,1]-.13)/.05))*smoothstep((unique[:,2]+.10)/.05)
for _ in range(10):
    for factor in (.45,-.46):unique+=factor*mask[:,None]*(adj@unique/np.maximum(degree[:,None],1)-unique)
p[body]=unique[inv]

# Place new body vertices within the original body block so part ranges remain valid.
order=np.r_[np.arange(body_end),np.arange(old_n,len(p)),np.arange(body_end,old_n)];remap=np.empty(len(p),int);remap[order]=np.arange(len(p))
p,u,bi,bw=[x[order] for x in (p,u,bi,bw)];tri=remap[tri].astype('<u4')
chunks=[];new_sub=[];offset=0
for i,(start,size) in enumerate(sub):
    chunk=tri.reshape(-1) if i==7 else remap[ix[start:start+size]].astype('<u4');chunks.append(chunk);new_sub.append([offset,len(chunk)]);offset+=len(chunk)
ix=np.concatenate(chunks).astype('<u4');norm=np.zeros_like(p)
norm[remap[np.arange(old_n)]]=n
body=np.unique(tri);_,inv=np.unique(np.round(p[body]*1e5).astype(np.int64),axis=0,return_inverse=True)
lookup=np.full(len(p),-1,int);lookup[body]=inv;area=np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]])
summed=np.zeros((inv.max()+1,3))
for k in range(3):np.add.at(summed,lookup[tri[:,k]],area)
length=np.linalg.norm(summed,axis=1);valid=length>1e-12;summed[valid]/=length[valid,None];summed[~valid]=[0,1,0];norm[body]=summed[inv]
added=len(p)-old_n
for item in r['parts']:
    item['vertexStart']=int(remap[item['vertexStart']])
    if item['part']=='body':item['vertices']+=added;item['triangles']=len(tri)
for mat,(start,size) in zip(m['materials'],new_sub):mat.update(indexStart=start,faceIndexCount=size)
m['counts'].update(vertices=len(p),indices=len(ix));m['generatedBy']+=' + sculpt_barefoot_ankle_v4.py';m['source']['modelName']='祀 蓝白泳装 · 赤脚脚踝曲面修正'
r['counts']=m['counts'];r['triangles']=len(ix)//3;r['barefoot']['surfaceSculpt']=dict(localSubdivisionPasses=2,addedVertices=added,profiles=profiles,method='Smooth anterior instep profile, preserved posterior heel contour, local Taubin fairing',previousAnkleSurfaceRejected=True)
args.out.mkdir(parents=True,exist_ok=False);(args.out/'textures').mkdir()
for src in (args.input/'textures').iterdir():
    if src.is_file():
        with (args.out/'textures'/src.name).open('xb') as f:f.write(src.read_bytes())
with (args.out/'si_model.bin').open('xb') as f:
    f.write(struct.pack('<II',0x5346474d,1))
    for ar in (p.astype('<f4'),norm.astype('<f4'),u,bi,bw,ix,bind,np.array(new_sub,'<u4')):f.write(ar.tobytes())
    for ids,delta in morphs:f.write(remap[ids].astype('<u4').tobytes());f.write(delta.tobytes())
emit_json(args.out/'si_model.json',m);emit_json(args.out/'conversion-report.json',r)
assert np.isfinite(p).all() and p[:,1].min()>-.00001
print(json.dumps({'counts':m['counts'],'sculpt':r['barefoot']['surfaceSculpt']}))
