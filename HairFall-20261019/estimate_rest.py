from pathlib import Path
import json
import numpy as np
from scipy.optimize import minimize

d=json.loads((Path(__file__).parent/'Project2/Assets/StreamingAssets/physics/si-physics.json').read_text(encoding='utf-8-sig'))
b=d['bodies'];group=[v for v in b if v['group']==4 and v['mode']!=0]
w=lambda x:np.clip(max(x['mass'],.001)**.25,.5,2)
mass=np.array([.2*w(x)/sum(w(y) for y in group) for x in b[87:103]])
nodes=np.array([x['position'] for x in b[86:103]])*.08
axis=nodes[-1,[0,2]]-nodes[0,[0,2]];axis/=np.linalg.norm(axis)
segments=np.diff(nodes,axis=0);horizontal=segments[:,[0,2]]@axis
length=np.sqrt(horizontal**2+segments[:,1]**2);theta=np.arctan2(horizontal,-segments[:,1]);rest=np.diff(np.r_[0,theta])
for bend in (.10,.16,.24,.35,.5):
    torque=np.array([sum(mass[k]*6.5*np.linalg.norm((nodes[k+1]-nodes[j])[[0,2]]) for k in range(j,16)) for j in range(16)])
    stiffness=np.maximum(.0002,torque/bend)
    def energy(angles):
        local=np.diff(np.r_[0,angles])-rest
        y=-np.cumsum(np.cos(angles)*length)
        return np.sum(mass*6.5*y)+.5*np.sum(stiffness*local**2)
    result=minimize(energy,theta,method='BFGS',options={'gtol':1e-9})
    print('bend',bend,'horizontal',round(float(np.sum(np.sin(result.x)*length)),3),'drop',round(float(np.sum(np.cos(result.x)*length)),3))
