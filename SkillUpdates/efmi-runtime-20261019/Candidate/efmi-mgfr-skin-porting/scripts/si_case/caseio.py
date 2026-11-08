"""MGFR native v1 IO and normals, shared by the case helpers."""
from pathlib import Path
import json,struct
import numpy as np

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

def normals(pos, triangles):
    tri=triangles.reshape(-1,3);result=np.zeros_like(pos,dtype=float)
    cross=np.cross(pos[tri[:,1]]-pos[tri[:,0]],pos[tri[:,2]]-pos[tri[:,0]])
    for k in range(3):np.add.at(result,tri[:,k],cross)
    lengths=np.linalg.norm(result,axis=1);valid=lengths>1e-12
    result[valid]/=lengths[valid,None];result[~valid]=[0,1,0]
    return result.astype('<f4')
