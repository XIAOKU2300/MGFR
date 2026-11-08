from pathlib import Path
import json,sys,hashlib,copy,struct,shutil
import numpy as np
from scipy.spatial import cKDTree

lab=Path(__file__).resolve().parent;root=lab.parent
sys.path.insert(0,str(root/'tools/skins'))
from build_swimsuit_v1 import read_base,normals
flat=root/'converted/skins/si-swimsuit-barefoot-ankle-v4';shod=root/'converted/skins/si-swimsuit-ready'
out=lab/'Skin';assert not out.exists();out.mkdir()
m,a,morphs=read_base(flat);sm,sa,_=read_base(shod)
p,n,uv,bi,bw,ix,bind,sub=a
fr=json.loads((flat/'conversion-report.json').read_text(encoding='utf8'))
sr=json.loads((shod/'conversion-report.json').read_text(encoding='utf8'))
fb=next(x for x in fr['parts'] if x['part']=='body');sb=next(x for x in sr['parts'] if x['part']=='body');shoe=next(x for x in sr['parts'] if x['part']=='shoes')
base_count=sb['vertices'];shift=fr['barefoot']['bodyVerticalShiftMetres'];old_n=len(p)
assert np.array_equal(uv[fb['vertexStart']:fb['vertexStart']+base_count],sa[2][sb['vertexStart']:sb['vertexStart']+base_count])
assert np.array_equal(bi[fb['vertexStart']:fb['vertexStart']+base_count],sa[3][sb['vertexStart']:sb['vertexStart']+base_count])
source_ids=np.arange(shoe['vertexStart'],shoe['vertexStart']+shoe['vertices'])
shoe_p=sa[0][source_ids].copy();shoe_p[:,1]+=shift
remap=np.full(len(sa[0]),-1,np.int64);remap[source_ids]=np.arange(old_n,old_n+len(source_ids))
shoe_tri=sa[5].reshape(-1,3);shoe_tri=shoe_tri[np.all(np.isin(shoe_tri,source_ids),axis=1)]
assert len(shoe_tri)==shoe['triangles']
new_shoe_tri=remap[shoe_tri].astype('<u4')
p=np.concatenate((p,shoe_p));n=np.concatenate((n,sa[1][source_ids]));uv=np.concatenate((uv,sa[2][source_ids]));bi=np.concatenate((bi,sa[3][source_ids]));bw=np.concatenate((bw,sa[4][source_ids]))
chunks=[];new_sub=[];offset=0
for slot,(start,count) in enumerate(sub):
    chunk=ix[start:start+count]
    if slot==8:chunk=np.r_[chunk,new_shoe_tri.reshape(-1)]
    chunks.append(chunk);new_sub.append([offset,len(chunk)]);offset+=len(chunk)
ix=np.concatenate(chunks).astype('<u4');sub=np.array(new_sub,'<u4')
m['counts'].update(vertices=len(p),indices=len(ix));m['generatedBy']+=' + ShoeLive append shoes; 40 authored morphs preserved'
m['boundsScaled']={'min':p.min(0).tolist(),'max':p.max(0).tolist()}
for mat,(start,count) in zip(m['materials'],sub):mat.update(indexStart=int(start),faceIndexCount=int(count))
with (out/'si_model.bin').open('xb') as f:
    f.write(struct.pack('<II',0x5346474d,1))
    for ar in (p,n,uv,bi,bw,ix,bind,sub):f.write(ar.tobytes())
    for ids,delta in morphs:f.write(ids.tobytes());f.write(delta.tobytes())
def emit(path,data):
    with path.open('x',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
emit(out/'si_model.json',m);shutil.copytree(flat/'textures',out/'textures');shutil.copyfile(flat/'skin.json',out/'skin.json')
# The first original body vertices have an exact UV/order correspondence. Extra
# v4 ankle vertices receive a local interpolated displacement; barefoot stays exact.
source_body=sa[0][sb['vertexStart']:sb['vertexStart']+base_count].copy();source_body[:,1]+=shift
flat_old=a[0][fb['vertexStart']:fb['vertexStart']+base_count]
body_delta=source_body-flat_old
added_ids=np.arange(fb['vertexStart']+base_count,fb['vertexStart']+fb['vertices'])
max_near=0.;foot_config={'height':float(-shoe_p[:,1].min()),'vertexCount':len(p),'morphs':[]}
for side,label in ((1,'Left'),(-1,'Right')):
    delta=np.zeros_like(p);body_ids=np.arange(fb['vertexStart'],fb['vertexStart']+base_count)
    selected=flat_old[:,0]*side>0
    delta[body_ids[selected]]=body_delta[selected]
    added=added_ids[p[added_ids,0]*side>0]
    dist,near=cKDTree(flat_old[selected]).query(p[added],k=4)
    w=1/np.maximum(dist,.00001)**2;w/=w.sum(1,keepdims=True)
    delta[added]=np.sum(body_delta[selected][near]*w[:,:,None],axis=1)
    max_near=max(max_near,float(dist[:,0].max()))
    target=p+delta
    nd=normals(target,ix[sub[7,0]:sub[7,0]+sub[7,1]])-n
    active=np.linalg.norm(delta,axis=1)>1e-7;nd[~active]=0
    filename=f'foot-{label.lower()}.bin'
    with (out/filename).open('xb') as f:f.write(delta.astype('<f4').tobytes());f.write(nd.astype('<f4').tobytes())
    foot_config['morphs'].append({'name':'ShoeFoot'+label,'file':filename,'side':side})
emit(out/'foot-pose.json',foot_config)
profile=copy.deepcopy(json.loads((root/'WardrobeAdapt-20261019/Package/barefoot_v4/wardrobe.json').read_text(encoding='utf8')))
profile.update(id='barefoot_v4_with_shoes',vertexCount=len(p),indexCount=len(ix),blendShapeCount=42,
    triangleBufferSha256=hashlib.sha256(ix.tobytes()).hexdigest(),positionBufferSha256=hashlib.sha256(p.tobytes()).hexdigest(),
    modelJsonSha256=hashlib.sha256((out/'si_model.json').read_bytes()).hexdigest(),modelBinarySha256=hashlib.sha256((out/'si_model.bin').read_bytes()).hexdigest())
prof=lab/'Profile';assert not prof.exists();shutil.copytree(root/'WardrobeAdapt-20261019/Package/barefoot_v4/parts',prof/'parts')
for side,suffix in ((1,'left'),(-1,'right')):
    t=new_shoe_tri[np.mean(p[new_shoe_tri,0],axis=1)*side>0]
    v=np.unique(t);points=p[v];target=np.array([side*.075,.16,-.035]);anchor=int(v[np.argmin(np.linalg.norm(points-target,axis=1))])
    name=f'parts/shoe_{suffix}.indices.bin'
    with (prof/name).open('xb') as f:f.write(t.tobytes())
    profile['parts'].append({'id':'shoe_'+suffix,'label':'左鞋' if side==1 else '右鞋','materialSlot':8,'indexFile':name,'indexSha256':hashlib.sha256(t.tobytes()).hexdigest(),
        'indexCount':int(t.size),'triangleCount':len(t),'anchors':[{'vertex':anchor,'position':p[anchor].tolist(),'normal':n[anchor].tolist(),'boneIndices':bi[anchor].astype(int).tolist(),'boneWeights':bw[anchor].tolist()}],
        'gripRadiusMetres':.05,'pullDistanceMetres':.10,'snapRadiusMetres':.07,'snapAngleDegrees':40.,'pullDirectionLocal':[0,-.35,-.9367497],
        'requiresClothOwnershipHandoff':False,'requiresFootPoseTransition':True,'clothOwner':'skinned'})
profile['footPose']={'id':'independent_left_right_heel_blends','height':foot_config['height'],'crossProfileEquipAllowed':False}
emit(prof/'wardrobe.json',profile)
emit(lab/'skin-checks.json',{'baseVerticesPreserved':bool(np.array_equal(p[:old_n],a[0])),'bones':len(bind),'authoredMorphs':len(morphs),'vertices':len(p),'shoeTriangles':len(shoe_tri),
    'nearestExtraAnkleVertexMetres':max_near,'soleLiftMetres':foot_config['height'],'sources':{str(src):hashlib.sha256(src.read_bytes()).hexdigest() for r in (flat,shod) for src in (r/'si_model.json',r/'si_model.bin')}})
print('skin:',len(p),'vertices; shoes:',len(shoe_tri),'triangles; heel lift',foot_config['height'])
