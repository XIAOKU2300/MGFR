import argparse, collections, json, math, pathlib, struct
p=argparse.ArgumentParser(description='Independent GLB v2 structural and animation check; standard library only.')
p.add_argument('glb'); p.add_argument('manifest'); p.add_argument('report'); a=p.parse_args()
GLB=pathlib.Path(a.glb); MAN=pathlib.Path(a.manifest); OUT=pathlib.Path(a.report)
if OUT.exists(): raise SystemExit(f'refusing to overwrite report: {OUT}')
buf=GLB.read_bytes(); bad=[]; warn=[]; checks=0
def ck(ok,msg):
 global checks
 checks+=1
 if not ok: bad.append(msg)
ck(len(buf)>=12,'GLB shorter than 12-byte header')
magic,version,total=struct.unpack_from('<4sII',buf,0); ck(magic==b'glTF',f'bad magic {magic!r}'); ck(version==2,f'GLB version {version}'); ck(total==len(buf),f'header length {total} != file size {len(buf)}')
off=12; chunks=[]
while off+8<=len(buf):
 size,typ=struct.unpack_from('<I4s',buf,off); off+=8; ck(off+size<=len(buf),f'chunk {typ!r} out of range')
 if off+size>len(buf): break
 chunks.append((typ,buf[off:off+size])); off+=size
ck(off==len(buf),'trailing or truncated bytes after chunks')
js=[x for t,x in chunks if t==b'JSON']; bins=[x for t,x in chunks if t==bytes([66,73,78,0])]
ck(len(js)==1,f'JSON chunk count {len(js)}'); ck(len(bins)==1,f'BIN chunk count {len(bins)}')
if not js or not bins: raise SystemExit('missing JSON or BIN chunk')
g=json.loads(js[0].rstrip(bytes([32,9,10,13,0])).decode('utf-8'),parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON constant '+x))); binary=bins[0]
def finitejson(x,path='$'):
 if isinstance(x,float) and not math.isfinite(x): bad.append(f'nonfinite JSON float at {path}')
 elif isinstance(x,dict):
  for k,v in x.items(): finitejson(v,path+'.'+str(k))
 elif isinstance(x,list):
  for i,v in enumerate(x): finitejson(v,f'{path}[{i}]')
finitejson(g); ck(g.get('asset',{}).get('version')=='2.0','asset.version is not 2.0')
ck(len(g.get('buffers',[]))==1,'expected exactly one GLB buffer')
if g.get('buffers'): ck(g['buffers'][0].get('byteLength',-1)<=len(binary),'declared buffer length exceeds BIN chunk')
views=g.get('bufferViews',[]); acc=g.get('accessors',[]); comp={5120:('b',1),5121:('B',1),5122:('h',2),5123:('H',2),5125:('I',4),5126:('f',4)}; dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT2':4,'MAT3':9,'MAT4':16}
for i,v in enumerate(views):
 start=v.get('byteOffset',0); size=v.get('byteLength',-1); ck(v.get('buffer',0)==0,f'bufferView {i} nonzero buffer'); ck(start>=0 and size>=0 and start+size<=len(binary),f'bufferView {i} exceeds BIN bounds')
 if 'byteStride' in v: ck(v['byteStride']%4==0 and 4<=v['byteStride']<=252,f'bufferView {i} invalid stride')
def rows(ai):
 x=acc[ai]; fmt,cs=comp[x['componentType']]; n=dim[x['type']]; count=x['count']; vi=x.get('bufferView'); ao=x.get('byteOffset',0)
 if vi is None: out=[(0,)*n for _ in range(count)]
 else:
  v=views[vi]; stride=v.get('byteStride',n*cs); base=v.get('byteOffset',0)+ao; out=[struct.unpack_from('<'+fmt*n,binary,base+j*stride) for j in range(count)]
 sp=x.get('sparse')
 if sp:
  z=sp['indices']; iv=views[z['bufferView']]; ifmt,ics=comp[z['componentType']]; ib=iv.get('byteOffset',0)+z.get('byteOffset',0); y=sp['values']; vv=views[y['bufferView']]; vb=vv.get('byteOffset',0)+y.get('byteOffset',0)
  for j in range(sp['count']):
   idx=struct.unpack_from('<'+ifmt,binary,ib+j*ics)[0]; ck(idx<count,f'accessor {ai} sparse index out of range')
   if idx<count: out[idx]=struct.unpack_from('<'+fmt*n,binary,vb+j*n*cs)
 return out
for i,x in enumerate(acc):
 ct=x.get('componentType'); ty=x.get('type'); count=x.get('count'); ao=x.get('byteOffset',0)
 ck(ct in comp,f'accessor {i} invalid component type {ct}'); ck(ty in dim,f'accessor {i} invalid dimension {ty}'); ck(isinstance(count,int) and count>=0,f'accessor {i} invalid count')
 if ct not in comp or ty not in dim or not isinstance(count,int) or count<0: continue
 n=dim[ty]; cs=comp[ct][1]; vi=x.get('bufferView')
 if vi is not None and vi<len(views):
  v=views[vi]; stride=v.get('byteStride',n*cs); need=ao+(count-1)*stride+n*cs if count else ao; ck(ao>=0 and need<=v.get('byteLength',-1),f'accessor {i} range exceeds view'); ck((v.get('byteOffset',0)+ao)%cs==0,f'accessor {i} misaligned')
 elif vi is not None: bad.append(f'accessor {i} bad view index {vi}')
 elif not x.get('sparse'): warn.append(f'accessor {i} has no data source')
 for k in ('min','max'):
  if k in x: ck(len(x[k])==n,f'accessor {i} {k} dimension mismatch')
 if ct==5126:
  for ri,row in enumerate(rows(i)):
   for ci,val in enumerate(row):
    if not math.isfinite(val): bad.append(f'accessor {i}[{ri}][{ci}] nonfinite')
meshes=g.get('meshes',[]); nodes=g.get('nodes',[]); skins=g.get('skins',[]); anims=g.get('animations',[])
for mi,m in enumerate(meshes):
 for pi,pr in enumerate(m.get('primitives',[])):
  at=pr.get('attributes',{}); vc=None
  for key,expected in [('POSITION','VEC3'),('NORMAL','VEC3'),('TEXCOORD_0','VEC2'),('JOINTS_0','VEC4'),('WEIGHTS_0','VEC4')]:
   if key in at:
    ai=at[key]; ck(ai<len(acc),f'mesh {mi} {key} bad accessor')
    if ai<len(acc):
     ck(acc[ai]['type']==expected,f'mesh {mi} {key} expected {expected}, got {acc[ai]["type"]}')
     if vc is None: vc=acc[ai]['count']
     else: ck(vc==acc[ai]['count'],f'mesh {mi} {key} vertex count differs')
  if 'POSITION' in at and at['POSITION']<len(acc): vc=acc[at['POSITION']]['count']
  ix=pr.get('indices')
  if ix is not None and ix<len(acc):
   ck(acc[ix]['type']=='SCALAR',f'mesh {mi} index accessor not SCALAR')
   for j,row in enumerate(rows(ix)):
    if vc is not None and row[0]>=vc: bad.append(f'mesh {mi} primitive {pi} index {j}={row[0]} >= {vc}')
for ni,node in enumerate(nodes):
 if 'mesh' not in node or 'skin' not in node: continue
 mi=node['mesh']; si=node['skin']; ck(mi<len(meshes),f'node {ni} invalid mesh'); ck(si<len(skins),f'node {ni} invalid skin')
 if mi>=len(meshes) or si>=len(skins): continue
 joint_count=len(skins[si].get('joints',[]))
 for pi,pr in enumerate(meshes[mi].get('primitives',[])):
  at=pr.get('attributes',{}); ji=at.get('JOINTS_0'); wi=at.get('WEIGHTS_0'); ck(ji is not None and wi is not None,f'node {ni} primitive {pi} missing JOINTS/WEIGHTS')
  if ji is None or wi is None or ji>=len(acc) or wi>=len(acc): continue
  jr=rows(ji); wr=rows(wi); ck(len(jr)==len(wr),f'node {ni} JOINTS/WEIGHTS length mismatch')
  for vi,(js,ws) in enumerate(zip(jr,wr)):
   for slot,j in enumerate(js):
    if j>=joint_count: bad.append(f'node {ni} JOINTS_0 vertex {vi} slot {slot}={j} >= skin joints {joint_count}')
   if any(w<0 for w in ws): bad.append(f'node {ni} vertex {vi} negative weights')
   sw=sum(ws)
   if any(w>0 for w in ws) and abs(sw-1)>1e-3: bad.append(f'node {ni} vertex {vi} weights sum {sw:.7g} outside 1±0.001')
maxdev=0.; durations={}; dup=0
for ai,an in enumerate(anims):
 sam=an.get('samplers',[]); ch=an.get('channels',[]); seen=set(); alltimes=[]
 for ci,c in enumerate(ch):
  si=c.get('sampler',-1); tar=c.get('target',{}); nd=tar.get('node'); path=tar.get('path'); ck(si<len(sam),f'animation {ai} channel {ci} bad sampler'); ck(nd is None or nd<len(nodes),f'animation {ai} channel {ci} bad target node')
  pair=(nd,path)
  if pair in seen: dup+=1; bad.append(f'animation {ai} duplicate target {pair}')
  seen.add(pair)
 for si,s in enumerate(sam):
  inp=s.get('input',-1); out=s.get('output',-1); interp=s.get('interpolation','LINEAR'); ck(inp<len(acc) and out<len(acc),f'animation {ai} sampler {si} invalid accessor')
  if inp<0 or out<0 or inp>=len(acc) or out>=len(acc): continue
  ck(acc[inp]['type']=='SCALAR' and acc[inp]['componentType']==5126,f'animation {ai} sampler {si} input must float SCALAR'); ts=[v[0] for v in rows(inp)]
  if any(ts[j+1]<=ts[j] for j in range(len(ts)-1)): bad.append(f'animation {ai} sampler {si} times not strictly increasing')
  alltimes+=ts; mult=3 if interp=='CUBICSPLINE' else 1; targets=[c.get('target',{}) for c in ch if c.get('sampler')==si]; isweights=bool(targets) and all(t.get('path')=='weights' for t in targets); expected=len(ts)*mult
  if isweights:
   morph=[]
   for t in targets:
    nd=t.get('node'); mi=nodes[nd].get('mesh') if nd is not None and nd<len(nodes) else None
    morph.append(max((len(q.get('targets',[])) for q in meshes[mi].get('primitives',[])),default=0) if mi is not None and mi<len(meshes) else 1)
   expected*=max(morph,default=1)
  ck(acc[out]['count']==expected,f'animation {ai} sampler {si} output count {acc[out]["count"]}, expected {expected}')
  for t in targets:
   path=t.get('path'); typ=acc[out]['type']
   if path in ('translation','scale'): ck(typ=='VEC3',f'animation {ai} {path} output must VEC3')
   if path=='rotation':
    ck(typ=='VEC4',f'animation {ai} rotation output must VEC4')
    if typ=='VEC4':
     qs=rows(out); qs=qs[1::3] if interp=='CUBICSPLINE' else qs
     for qi,q in enumerate(qs):
      norm=math.sqrt(sum(z*z for z in q)); dev=abs(norm-1); maxdev=max(maxdev,dev)
      if not math.isfinite(norm) or dev>1e-3: bad.append(f'animation {ai} quaternion {qi} norm {norm:.8g}')
 if alltimes: durations[an.get('name',str(ai))]=(min(alltimes),max(alltimes))
manifest=json.loads(MAN.read_text(encoding='utf-8')); src=manifest.get('clips',[]); comp=[]; labels=[x.get('name') for x in anims]
for i,c in enumerate(src):
 glb_name=labels[i] if i<len(labels) else None; expname=c.get('label') or c.get('name'); d=durations.get(glb_name); gd=d[1]-d[0] if d else None; ex=float(c.get('duration',0)); status='match' if glb_name==expname and gd is not None and abs(gd-ex)<=1e-4 else 'mismatch'; comp.append((i,expname,glb_name,status,ex,gd))
lines=['# Independent GLB validation','','Parsed directly with Python standard library. No converter or official validator was run.','',f'- GLB: `{GLB.name}`, {len(buf):,} bytes; version {version}; declared length {total:,}.',f'- Animations: {len(anims)}; meshes: {len(meshes)}; nodes: {len(nodes)}; skins: {len(skins)}.',f'- Accessors: {len(acc)}; bufferViews: {len(views)}; BIN: {len(binary):,} bytes.',f'- Structural checks: {checks}; failures: {len(bad)}; warnings: {len(warn)}.',f'- Maximum rotation quaternion norm deviation: {maxdev:.8g}; duplicate animation node/path pairs: {dup}.',f'- motions-v3 comparison by order and display label: {len(comp)} clips; statuses `{dict(collections.Counter(x[3] for x in comp))}`.','', '| # | manifest motion | GLB animation | status | source s | GLB s |','|---:|---|---|---|---:|---:|']
for i,en,gn,s,e,d in comp: lines.append(f'| {i+1} | `{en}` | `{gn}` | {s} | {e:.6f} | {d if d is not None else "missing" if False else "" if d is None else f"{d:.6f}"} |')
if bad: lines+=['','## Failures']+[f'- {x}' for x in bad[:60]]
if warn: lines+=['','## Warnings']+[f'- {x}' for x in warn[:60]]
with OUT.open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(lines)+'\n')
print(f'animations={len(anims)} meshes={len(meshes)} nodes={len(nodes)} accessors={len(acc)} views={len(views)} checks={checks} failures={len(bad)} warnings={len(warn)} quaternion_max_deviation={maxdev:.8g} manifest={dict(collections.Counter(x[3] for x in comp))}')
for x in bad[:20]:print('FAIL',x)
print('report',OUT)
