"""Unity v22 embedded type-tree reader including declarative managed references.
No managed code is loaded or executed. Unknown schemas and unread bytes fail.
"""
import sys,struct
sys.path.insert(0,'H:/MGFR/work/si-animation-20261019')
from bundle_reader import Reader
from typetree_reader import COMMON,PRIMITIVES
def read_file(data):
 r=Reader(data);r.take(8);assert r.get('I')==22;r.take(4);endian=r.get('B');r.take(3);r.get('I');size=r.get('q');start=r.get('q');r.get('q');assert size==len(data)
 r.endian='<' if not endian else '>';r.cstring();r.get('i');assert r.get('B')
 def serialized_type(reference=False):
  kind=r.get('i');r.get('B');script=r.get('h')
  if kind==114 or (reference and script>=0):r.take(16)
  r.take(16);count=r.get('i');strings=r.get('i');raw=r.take(count*32);buf=r.take(strings)
  def string(p):
   if p&0x80000000:return COMMON[p&0x7fffffff]
   return buf[p:buf.index(b'\0',p)].decode()
  nodes=[]
  for i in range(count):
   ver,level,flags,typ,name,bytesize,index,meta,ref=struct.unpack_from('<HBBIIiiiQ',raw,i*32)
   nodes.append({'type':string(typ),'name':string(name),'level':level,'align':bool(meta&0x4000),'children':[]})
  stack=[]
  for n in nodes:
   while stack and stack[-1]['level']>=n['level']:stack.pop()
   if stack:stack[-1]['children'].append(n)
   stack.append(n)
  key=None
  if reference:key=tuple(r.cstring().decode() for _ in range(3))
  else:r.take(r.get('i')*4)
  return {'class_id':kind,'tree':nodes[0],'key':key}
 types=[serialized_type() for _ in range(r.get('i'))];objects=[]
 for _ in range(r.get('i')):
  r.pos=(r.pos+3)&~3;path=r.get('q');offset=r.get('q')+start;length=r.get('I');kind=r.get('i');assert start<=offset<=offset+length<=len(data)
  objects.append({'path_id':path,'data':data[offset:offset+length],**types[kind]})
 for _ in range(r.get('i')):r.get('i');r.pos=(r.pos+3)&~3;r.get('q')
 externals=[]
 for _ in range(r.get('i')):r.cstring();r.take(20);externals.append(r.cstring().decode())
 refs={}
 for _ in range(r.get('i')):
  t=serialized_type(True);refs[t['key']]=t['tree']
 r.cstring()
 def parse_object(obj):
  rr=Reader(obj['data'],'<')
  def parse(n):
   typ=n['type'];children=n['children']
   if typ=='ReferencedObject':
    rid=parse(children[0]);rt=parse(children[1]);key=(rt['class'],rt['ns'],rt['asm'])
    if not rt['class']:value={'rid':rid,'type':rt,'data':None}
    else:
     if key not in refs:raise ValueError(f'Unknown managed type {key}')
     print('managed',rid,key,'offset',rr.pos,'next',rr.data[rr.pos:rr.pos+40].hex());value={'rid':rid,'type':rt,'data':parse(refs[key])}
   elif typ=='string':value=rr.take(rr.get('i')).decode();rr.pos=(rr.pos+3)&~3
   elif typ=='TypelessData':value=rr.take(rr.get('i'))
   elif typ in PRIMITIVES:value=rr.get(PRIMITIVES[typ])
   elif typ=='Array':
    count=rr.get('i');assert 0<=count<=len(rr.data),(n['name'],rr.pos,count,rr.data[max(0,rr.pos-48):rr.pos+16].hex())
    element=children[1];value=rr.take(count) if element['type'] in ['UInt8','char'] else [parse(element) for _ in range(count)]
   elif len(children)==1 and children[0]['type']=='Array':value=parse(children[0])
   elif children:value={c['name']:parse(c) for c in children}
   else:raise ValueError('Unknown leaf '+typ)
   if n['align']:rr.pos=(rr.pos+3)&~3
   return value
  v=parse(obj['tree']);assert rr.pos==len(rr.data),(rr.pos,len(rr.data));return v
 return objects,refs,externals,parse_object
