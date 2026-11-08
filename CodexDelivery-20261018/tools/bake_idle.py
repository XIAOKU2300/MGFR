"""Bake the supplied VMD against the actual PMX rig. Originals are read-only."""
from pathlib import Path
import bisect, collections, json, math, struct, sys
import numpy as np

ROOT = Path('H:/MGFR')
OUT = ROOT / 'CodexDelivery-20261018'
sys.path.insert(0, str(ROOT / 'tools/pmx'))
from pmx_reader import read_pmx

def unit(q):
    return q / np.linalg.norm(q)

def mul(a,b):
    return np.r_[a[3]*b[:3]+b[3]*a[:3]+np.cross(a[:3],b[:3]), a[3]*b[3]-np.dot(a[:3],b[:3])]

def inv(q):
    return q*np.array([-1,-1,-1,1])

def rotate(q,v):
    t=2*np.cross(q[:3],v)
    return v+q[3]*t+np.cross(q[:3],t)

def slerp(a,b,t):
    d=float(np.dot(a,b))
    if d<0: b=-b; d=-d
    d=min(d,1)
    if d>.9995: return unit(a+(b-a)*t)
    theta=math.acos(d)
    return (math.sin((1-t)*theta)*a+math.sin(t*theta)*b)/math.sin(theta)

def between(a,b):
    a=a/np.linalg.norm(a); b=b/np.linalg.norm(b); d=float(np.dot(a,b))
    if d<-.99999:
        axis=np.cross(a,[1,0,0])
        if np.linalg.norm(axis)<1e-6: axis=np.cross(a,[0,0,1])
        return np.r_[axis/np.linalg.norm(axis),0]
    return unit(np.r_[np.cross(a,b),1+d])

def bezier(t,raw,channel):
    x1,y1,x2,y2=(raw[channel+k]/127 for k in (0,4,8,12))
    lo,hi=0.,1.
    for _ in range(18):
        u=(lo+hi)/2; v=1-u
        x=3*v*v*u*x1+3*v*u*u*x2+u*u*u
        if x<t:lo=u
        else:hi=u
    u=(lo+hi)/2; v=1-u
    return 3*v*v*u*y1+3*v*u*u*y2+u*u*u

model=read_pmx(str(next(ROOT.glob('*/祀.pmx'))))
names={b.name:i for i,b in enumerate(model.bones)}
data=next(ROOT.glob('Idle2*.vmd')).read_bytes()
n=struct.unpack_from('<I',data,50)[0]
tracks=collections.defaultdict(list)
for k in range(n):
    o=54+k*111; name=data[o:o+15].split(b'\0')[0].decode('cp932',errors='replace')
    f,*v=struct.unpack_from('<I7f',data,o+15)
    tracks[name].append((f,np.array(v[:3])*.08,unit(np.array(v[3:])),data[o+47:o+111]))
for t in tracks.values():t.sort(key=lambda k:k[0])

def sample(track,f):
    if f<=track[0][0]:return track[0][1],track[0][2]
    if f>=track[-1][0]:return track[-1][1],track[-1][2]
    k=bisect.bisect_right([x[0] for x in track],f); a,b=track[k-1:k+1]; u=(f-a[0])/(b[0]-a[0])
    p=np.array([a[1][j]+(b[1][j]-a[1][j])*bezier(u,b[3],j) for j in range(3)])
    return p,slerp(a[2],b[2],bezier(u,b[3],3))

bones=model.bones; count=len(bones); parents=[b.parent_index for b in bones]
absolute=np.array([b.position for b in bones])*.08
rest=np.array([absolute[i]-(absolute[p] if p>=0 else 0) for i,p in enumerate(parents)])
identity=np.array([0.,0.,0.,1.])
matched={names[name]:t for name,t in tracks.items() if name in names}
# The VMD has a different skirt/hair rig. No positional/name-index guessing.
owned=sorted(set(matched)|{i for i,b in enumerate(bones) if b.inherit_parent_index>=0})
owned=[i for i in owned if i<81 or i in (738,739,740,742,743,744)]
frames=[]; max_error=0
for frame in range(131):
    q=np.tile(identity,(count,1)); pos=rest.copy()
    for i,t in matched.items():
        dp,dq=sample(t,frame); pos[i]+=dp; q[i]=dq
    authored=q.copy()
    for i,b in enumerate(bones):
        if b.fixed_axis is not None:
            axis=np.array(b.fixed_axis); axis/=np.linalg.norm(axis)
            q[i]=unit(np.r_[axis*np.dot(q[i,:3],axis),q[i,3]])
        if b.inherit_parent_index>=0 and i<81:
            q[i]=mul(q[i],slerp(identity,authored[b.inherit_parent_index],b.inherit_weight))
    def world(i,cache):
        if i in cache:return cache[i]
        p=parents[i]
        if p<0: result=(pos[i],q[i])
        else:
            pp,pq=world(p,cache); result=(pp+rotate(pq,pos[i]),mul(pq,q[i]))
        cache[i]=result; return result
    # Actual PMX leg and toe chains, including its hinge bounds.
    for ik_index in (7,10,8,11):
        ik=bones[ik_index].ik; goal=world(ik_index,{})[0]
        for iteration in range(ik.loop_count):
            if np.linalg.norm(world(ik.target_index,{})[0]-goal)<.00008:break
            for link in ik.links:
                i=link.bone_index; cache={}; joint,jq=world(i,cache)
                eff=world(ik.target_index,cache)[0]
                a=rotate(inv(jq),eff-joint); b=rotate(inv(jq),goal-joint)
                if np.linalg.norm(a)<1e-8 or np.linalg.norm(b)<1e-8:continue
                delta=between(a,b); angle=2*math.acos(min(1,abs(delta[3])))
                if angle>ik.angle_limit_per_loop:delta=slerp(identity,delta,ik.angle_limit_per_loop/angle)
                q[i]=unit(mul(q[i],delta))
                if link.has_limits:
                    # Both actual knee links are PMX X-only hinges.
                    x=2*math.atan2(q[i,0],q[i,3]); x=(x+math.pi)%(2*math.pi)-math.pi
                    x=float(np.clip(x,link.limit_min[0],link.limit_max[0]))
                    q[i]=np.array([math.sin(x/2),0,0,math.cos(x/2)])
        max_error=max(max_error,float(np.linalg.norm(world(ik.target_index,{})[0]-goal)))
    # Deformation leg duplicates inherit the SOLVED FK, not their pre-IK values.
    for i in (738,739,740,742,743,744):q[i]=q[bones[i].inherit_parent_index]
    frames.append((pos[owned]-rest[owned],q[owned].copy()))
# Close the authored seam over 0.33 seconds; the first segment starts held.
for f in range(120,131):
    t=(f-120)/10; t=t*t*t*(t*(t*6-15)+10)
    p,q=frames[f]; p=p*(1-t)+frames[0][0]*t
    q=np.array([slerp(a,b,t) for a,b in zip(q,frames[0][1])]);frames[f]=(p,q)
dest=OUT/'Motion';dest.mkdir(parents=True,exist_ok=True)
with (dest/'idle.bin').open('xb') as out:
    out.write(struct.pack('<4sIIf',b'IDLE',len(owned),len(frames),30.))
    out.write(struct.pack('<'+'i'*len(owned),*owned))
    for p,q in frames:out.write(np.c_[p,q].astype('<f4').tobytes())
report=dict(matched_tracks=[bones[i].name for i in matched],unmatched_tracks=[name for name in tracks if name not in names],
    baked_bones=[bones[i].name for i in owned],frames=len(frames),fps=30,duration=130/30,
    max_ik_error_m=max_error,loop_position_error=float(np.max(np.abs(frames[0][0]-frames[-1][0]))),
    loop_quaternion_error=float(np.max(np.abs(frames[0][1]-frames[-1][1]))),
    morph_policy='Live lips/blink own morphs. VMD morphs intentionally excluded.',
    physics_policy='Unmatched skirt/hair tracks excluded; separate skirt solver.')
with (dest/'bake-report.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)},ensure_ascii=False))
