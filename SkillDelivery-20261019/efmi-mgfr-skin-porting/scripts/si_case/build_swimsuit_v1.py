"""Read-only EFMI -> independent MGFR skin. All outputs must be new paths.

Requires existing numpy, scipy and Pillow. No Blender or game process required.
"""
from pathlib import Path
import argparse, copy, hashlib, json, shutil, struct
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image

def emit_json(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def read_base(root):
    model = json.loads((root/'si_model.json').read_text(encoding='utf-8-sig'))
    blob = (root/'si_model.bin').read_bytes()
    assert struct.unpack_from('<II', blob) == (0x5346474d, 1)
    n, c, off = model['counts']['vertices'], model['counts'], 8
    arrays = []
    for dtype, shape in [('<f4',(n,3)),('<f4',(n,3)),('<f4',(n,2)),('<u2',(n,4)),('<f4',(n,4)),('<u4',(c['indices'],)),('<f4',(c['bones'],4,4)),('<u4',(c['materials'],2))]:
        size = int(np.prod(shape)); a = np.frombuffer(blob,dtype,size,off).reshape(shape).copy()
        off += a.nbytes; arrays.append(a)
    morphs=[]
    for morph in model['blendShapes']:
        count=morph['vertexCount']; ids=np.frombuffer(blob,'<u4',count,off).copy();off+=count*4
        delta=np.frombuffer(blob,'<f4',count*3,off).reshape(-1,3).copy();off+=count*12
        morphs.append((ids,delta))
    assert off == len(blob)
    return model,arrays,morphs

def component(root, index):
    mesh=root/'Meshes'; stem=f'Component{index}'
    raw=(mesh/f'{stem}_VB0.buf').read_bytes()
    pos=np.ndarray((len(raw)//16,3),'<f4',raw,strides=(16,4)).copy()[:,[0,2,1]]*[-1,1,1]
    uvraw=(mesh/f'{stem}_VB1.buf').read_bytes(); stride=len(uvraw)//len(pos)
    uv=np.ndarray((len(pos),2),'<f4',uvraw,strides=(stride,4)).copy();uv[:,1]=1-uv[:,1]
    blend=np.fromfile(mesh/f'{stem}_VB2.buf','<u2').reshape(-1,8)
    weights=blend[:,:4].astype(float);weights/=np.maximum(weights.sum(1,keepdims=True),1)
    # Check the declared index format, not the resource stride (6 is a triangle).
    ini=(root/'mod.ini').read_text(encoding='utf-8-sig')
    section=ini.split(f'[Resource_{stem}_IB]')[1].split('\n[')[0]
    dtype='<u2' if 'R16_UINT' in section else '<u4'
    indices=np.fromfile(mesh/f'{stem}_IB.buf',dtype).astype(np.uint32)
    assert indices.max()<len(pos)
    return pos,uv,blend[:,4:].copy(),weights,indices

def dense(ids, weights, count):
    result=np.zeros((len(ids),count),dtype=np.float64)
    for k in range(4):np.add.at(result,(np.arange(len(ids)),ids[:,k]),weights[:,k])
    return result

def top4(weights):
    ids=np.argsort(weights,axis=1)[:,-4:][:,::-1]
    w=np.take_along_axis(weights,ids,axis=1);w/=np.maximum(w.sum(1,keepdims=True),1e-12)
    return ids.astype('<u2'),w.astype('<f4')

def arm_pose(pos, gids, weights, angle):
    result=pos.copy()
    for side,lo,hi,pivot in [(1,304,329,[.105,1.325,.002]),(-1,330,355,[-.105,1.325,.002])]:
        influence=np.sum(weights*((gids>=lo)&(gids<=hi)),axis=1)
        t=np.deg2rad(side*angle);rot=np.array([[np.cos(t),-np.sin(t),0],[np.sin(t),np.cos(t),0],[0,0,1]])
        turned=(pos-pivot)@rot.T+pivot
        result+=(turned-pos)*influence[:,None]
    return result

def normals(pos, triangles):
    tri=triangles.reshape(-1,3);result=np.zeros_like(pos,dtype=float)
    cross=np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]])
    for k in range(3):np.add.at(result,tri[:,k],cross)
    lengths=np.linalg.norm(result,axis=1);valid=lengths>1e-12
    result[valid]/=lengths[valid,None];result[~valid]=[0,1,0]
    return result.astype('<f4')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--arm-angle',type=float,default=13.115)
    args=ap.parse_args(); out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    m,a,morphs=read_base(args.base);p,norm,uv,bi,bw,oldidx,_,_=a
    baseline_hash={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [args.base/'si_model.json',args.base/'si_model.bin',args.source/'mod.ini']}
    parts={i:component(args.source,i) for i in (0,1,3,5,10,12,14)}
    # Establish winding against the unchanged original hair, not a visual guess.
    hp,_,_,_,hi=parts[1]; d,j=cKDTree(p).query(hp)
    ht=hi.reshape(-1,3);cross=np.cross(hp[ht[:,1]]-hp[ht[:,0]],hp[ht[:,2]]-hp[ht[:,0]])
    agreement=np.sum(cross*norm[j[ht]].mean(1),axis=1);flip=bool(np.median(agreement[np.abs(agreement)>1e-12])<0)
    # Learn game-group -> existing PMX weights from the new body's nearest old skin.
    body=parts[5]; used=np.unique(body[4][:61710]); bp=arm_pose(body[0][used],body[2][used],body[3][used],args.arm_angle)
    skinmat=m['materials'][7];skinids=np.unique(oldidx[skinmat['indexStart']:skinmat['indexStart']+skinmat['faceIndexCount']])
    dist,near=cKDTree(p[skinids]).query(bp,k=4);kernel=1/np.maximum(dist,.0002)**2;kernel/=kernel.sum(1,keepdims=True)
    target=np.zeros((len(bp),828),float)
    for k in range(4):target+=dense(bi[skinids[near[:,k]]],bw[skinids[near[:,k]]],828)*kernel[:,k,None]
    game=dense(body[2][used],body[3][used],518);support=game.sum(0);active=np.flatnonzero(support>.005)
    compact=game[:,active];ridge=.01
    fitted=np.linalg.solve(compact.T@compact+ridge*np.eye(len(active)),compact.T@target)
    fitted=np.maximum(fitted,0);fitted/=np.maximum(fitted.sum(1,keepdims=True),1e-12)
    groupmap=np.zeros((518,828),float);groupmap[active]=fitted
    # Keep the PMX head/hair and their original morph vertex IDs via an explicit remap.
    kept=(0,1,2,3,4,5,6,11,12,13)
    old_kept=np.unique(np.concatenate([oldidx[x['indexStart']:x['indexStart']+x['faceIndexCount']] for x in m['materials'] if x['index'] in kept]))
    remap=np.full(len(p),-1,np.int64);remap[old_kept]=np.arange(len(old_kept))
    positions=[p[old_kept]];ns=[norm[old_kept]];uvs=[uv[old_kept]];bis=[bi[old_kept]];bws=[bw[old_kept]]
    materials=copy.deepcopy(m['materials']);indices=[np.empty(0,'<u4') for _ in range(15)];materials.append(copy.deepcopy(materials[8]))
    materials[14].update(index=14,name='SwimsuitTail')
    for k in kept:
        mat=materials[k];indices[k]=remap[oldidx[mat['indexStart']:mat['indexStart']+mat['faceIndexCount']]].astype('<u4')
    treeskin=cKDTree(bp); audit=[]
    # Native default: body variant 0, horns/tail/shoes/sunglasses/sheer pieces on.
    # Component 9/11 are original floating effects, not clothing; 15/16 are CPU posed.
    draw=[(0,0,2316,9,'horn'),(3,1692,5976,14,'tail'),(3,7668,3210,8,'accessory'),(3,11988,15360,8,'bra'),
          (3,27348,702,8,'earrings'),(3,28050,0,8,'unused'),(3,28134,2196,8,'hair_ribbon'),(3,30330,2805,8,'left_wrist'),
          (3,33135,2568,8,'leg_accessory'),(3,35703,7008,8,'bottom'),(3,42711,846,8,'right_wrist'),(3,43557,7527,8,'shoes'),
          (3,51084,1140,8,'sunglasses'),(3,52224,2148,14,'tail_accessory'),(5,0,61710,7,'body'),
          (10,0,5376,14,'tail_base'),(12,0,2958,14,'tail_detail'),
          (14,0,15288,10,'sleeves'),(14,15288,8058,10,'bra_frill'),(14,23346,16599,10,'skirt')]
    for ci,start,count,mi,name in draw:
        if not count:continue
        sp,suv,gi,gw,ii=parts[ci];tri=ii[start:start+count].copy();unique,inverse=np.unique(tri,return_inverse=True)
        localtri=inverse.astype('<u4').reshape(-1,3)
        if flip:localtri=localtri[:,[0,2,1]]
        gp=sp[unique];gids=gi[unique];weights=gw[unique]
        posed=arm_pose(gp,gids,weights,args.arm_angle)
        learned=np.zeros((len(unique),828));known=np.zeros(len(unique))
        for k in range(4):
            rows=groupmap[gids[:,k]];learned+=rows*weights[:,k,None];known+=(rows.sum(1)>.5)*weights[:,k]
        # Explicit anchoring avoids assigning earrings to face expression bones.
        if name in ('horn','earrings','hair_ribbon','sunglasses'):
            learned[:]=0;learned[:,17]=1;known[:]=1;posed=gp
        elif name in ('tail','tail_accessory','tail_base','tail_detail'):
            dd,jj=cKDTree(p).query(gp);learned=dense(bi[jj],bw[jj],828);known[:]=1;posed=gp
        else:
            dd,jj=treeskin.query(posed)
            fallback=target[jj]
            if name=='skirt':
                # v1 is a body-bound skirt, not a new cloth simulation.
                fallback=np.zeros_like(fallback);fallback[:,12]=1
            if name=='sleeves':
                # Unknown decorative groups follow the arm, never the nearby thigh.
                fallback=np.zeros_like(fallback)
                for side,bone in [(1,35),(-1,61)]:fallback[gp[:,0]*side>=0,bone]=1
                armknown=np.sum(weights*((gids>=304)&(gids<=355)),axis=1)
                for side,pivot in [(1,np.array([.105,1.325,.002])),(-1,np.array([-.105,1.325,.002]))]:
                    mask=gp[:,0]*side>0;t=np.deg2rad(side*args.arm_angle);rot=np.array([[np.cos(t),-np.sin(t),0],[np.sin(t),np.cos(t),0],[0,0,1]])
                    turned=(gp-pivot)@rot.T+pivot
                    posed[mask]+=(turned-gp)[mask]*(1-armknown[mask,None])
            learned+=fallback*(1-known[:,None])
        ib,wb=top4(learned);offset=sum(len(x) for x in positions)
        positions.append(posed.astype('<f4'));ns.append(normals(posed,localtri));uvs.append(suv[unique].astype('<f4'));bis.append(ib);bws.append(wb)
        indices[mi]=np.concatenate([indices[mi],localtri.reshape(-1)+offset]).astype('<u4')
        audit.append(dict(part=name,component=ci,vertices=len(unique),triangles=count//3,material=mi,learnedWeightFraction=float(np.mean(known))))
    pos=np.concatenate(positions);normal=np.concatenate(ns);uv=np.concatenate(uvs);bi=np.concatenate(bis);bw=np.concatenate(bws)
    tex=out/'textures';tex.mkdir()
    for f in (args.base/'textures').iterdir():
        if f.is_file():
            with (tex/f.name).open('xb') as dest:dest.write(f.read_bytes())
    # PNGs retain the source alpha. Normal/light maps are provided for future shader wiring.
    texture_specs={'swimsuit_cloth_D.png':'*7114cec0*','swimsuit_cloth_N.png':'*d11b4e0b*','swimsuit_cloth_L.png':'*dea730f0*',
                   'swimsuit_body_D.png':'*9e07785e*','swimsuit_body_N.png':'*2483060d*'}
    texture_audit=[]
    for name,pattern in texture_specs.items():
        f=next((args.source/'Textures').glob(pattern));im=Image.open(f).convert('RGBA')
        with (tex/name).open('xb') as dest:im.save(dest,format='PNG')
        texture_audit.append(dict(file=name,source=str(f),width=im.width,height=im.height))
    for mi,name in [(7,'swimsuit_body_D.png'),(8,'swimsuit_cloth_D.png'),(10,'swimsuit_cloth_D.png')]:materials[mi]['textureFile']=name
    materials[14]['textureFile']=m['materials'][8]['textureFile']
    texture_list=copy.deepcopy(m['textures'])
    for item in texture_audit:
        texture_list.append(dict(index=len(texture_list),declared=item['source'],route='EFMI DDS decoded to PNG',file=item['file'],bytes=(tex/item['file']).stat().st_size))
    for mat in materials:
        mat['texture']=next((t['index'] for t in texture_list if t['file']==mat.get('textureFile')),-1)
    sub=[];offset=0
    for k,mat in enumerate(materials):
        mat.update(index=k,indexStart=offset,faceIndexCount=len(indices[k]));sub.append([offset,len(indices[k])]);offset+=len(indices[k])
    idx=np.concatenate(indices)
    # The legacy base JSON stores absolute rest coordinates in localScaled.
    # Repair only this new skin; the original data is never edited.
    absolute=np.array([b['localScaled'] for b in m['bones']]) if m['bones'][17]['positionScaled'][1]>3 else np.array([b['positionScaled'] for b in m['bones']])
    bind=np.tile(np.eye(4),(828,1,1));bind[:,:3,3]=-absolute
    for k,b in enumerate(m['bones']):
        b['positionScaled']=absolute[k].tolist();b['localScaled']=(absolute[k]-(absolute[b['parent']] if b['parent']>=0 else 0)).tolist()
    newmorph=[]
    for shape,(ids,delta) in zip(m['blendShapes'],morphs):
        mask=remap[ids]>=0;newids=remap[ids[mask]].astype('<u4');newdelta=delta[mask].astype('<f4');shape['vertexCount']=len(newids);newmorph.append((newids,newdelta))
    m['materials']=materials;m['textures']=texture_list;m['counts'].update(vertices=len(pos),indices=len(idx),materials=len(materials),textures=len(texture_list))
    m['boundsScaled']={'min':pos.min(0).tolist(),'max':pos.max(0).tolist()};m['generatedBy']='tools/skins/build_swimsuit_v1.py'
    m['coordinateNote']='EFMI position -> MGFR: (-x,z,y), UV V flipped; arms raised 13.115 degrees to the PMX rest pose; corrected parent-relative rest/bind coordinates.'
    m['source']['modelName']='祀 蓝白泳装 / standalone MGFR skin'
    with (out/'si_model.bin').open('xb') as f:
        f.write(struct.pack('<II',0x5346474d,1))
        for ar in (pos.astype('<f4'),normal.astype('<f4'),uv.astype('<f4'),bi.astype('<u2'),bw.astype('<f4'),idx.astype('<u4'),bind.astype('<f4'),np.array(sub,'<u4')):f.write(ar.tobytes())
        for ids,delta in newmorph:f.write(ids.tobytes());f.write(delta.tobytes())
    emit_json(out/'si_model.json',m)
    assert np.all(np.isfinite(pos)) and np.all(np.isfinite(normal)) and idx.max()<len(pos)
    assert bi.max()<828 and np.max(np.abs(bw.sum(1)-1))<1e-5
    checks=dict(counts=m['counts'],triangles=len(idx)//3,bounds=m['boundsScaled'],armAngleDegrees=args.arm_angle,sourceWindingFlipped=flip,
                boneNamesAndOrderPreserved=True,blendShapeNamesPreserved=True,sourceHashes=baseline_hash,parts=audit,textures=texture_audit,
                limitations=['v1 body-bound swimsuit cloth, no new cloth simulation','Existing stylized shader overrides must use swimsuit normal/light maps instead of original costume maps'],
                maxWeightSumError=float(np.max(np.abs(bw.sum(1)-1))),finitePositions=True)
    emit_json(out/'conversion-report.json',checks)
    for f,digest in baseline_hash.items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==digest
    print(json.dumps({k:checks[k] for k in ('counts','triangles','maxWeightSumError','sourceWindingFlipped')},ensure_ascii=False))

if __name__=='__main__':main()
