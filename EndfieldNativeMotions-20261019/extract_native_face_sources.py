"""Resolve only selected native facial config/emotion assets with exact path checks."""
from pathlib import Path
import sys,json,struct,hashlib,base64
ROOT=Path(__file__).resolve().parent;WORK=Path('H:/MGFR/work/si-animation-20261019');OUT=ROOT/'face-sources-v1';OUT.mkdir(exist_ok=False)
sys.path.insert(0,str(WORK))
from extract_verified import connect,read_payload
from bundle_reader import Helper,read_bundle
from typetree_reader import tree_objects,read_object
from map_si_resources import string
raw=next((WORK/'probe-payloads').glob('*_StringPathHash.bin')).read_bytes();start,count=struct.unpack_from('<II',raw);cursor=start;selected={}
terms=['data_facemorph_avatar_jsspsi.asset','data_facialmorph_emotion_smile01.asset','data_facialmorph_emotion_smile02.asset','data_facialmorph_emotion_smile03.asset','data_facialmorph_emotion_happys.asset','data_facialmorph_emotion_shya.asset']
for _ in range(count):
 n=struct.unpack_from('<I',raw,cursor)[0];name=string(raw,cursor)
 if any(name.lower().endswith(t) for t in terms):selected[cursor-start]={'path':name}
 cursor+=n+6
byhash={}
for i in range(count):
 offset,n=struct.unpack_from('<II',raw,8+i*8)
 for j in range(n):
  _,h,p=struct.unpack_from('<IQI',raw,offset+j*16)
  if p in selected:byhash.setdefault(h,[]).append(selected[p])
data=(WORK/'verified-payloads/manifest-decoded.bin').read_bytes();tables=[];cursor=156
for width in [32,56,48]:
 size,n=struct.unpack_from('<II',data,cursor);assert size==4+n*width;tables.append((cursor+8,n,width));cursor+=size+4
payload=cursor+4;asset_start,asset_count,_=tables[0];asset_values=asset_start+asset_count*8;bundle_start,bundle_count,_=tables[2]
db=connect();codec=Helper('BrotliServer.dll');cipher=Helper('OfflineDecoder.dll');report=[];done=set()
def encode(value):
 if isinstance(value,bytes):return {'encoding':'base64','byteLength':len(value),'data':base64.b64encode(value).decode()}
 raise TypeError(type(value).__name__)
try:
 for i in range(asset_count):
  h,ptr,bundle,size,padding=struct.unpack_from('<QIIII',data,asset_values+i*24)
  if h not in byhash:continue
  p=payload+ptr;length=struct.unpack_from('<I',data,p)[0];actual=codec.decode(data[p+4:p+4+length]).decode('utf-16-le')
  matches=[x for x in byhash[h] if x['path'].lower()==actual.lower()]
  if not matches:continue
  offset=bundle_start+bundle*48;ordinal,pointer,*_=struct.unpack_from('<6I',data,offset);assert ordinal==bundle
  name=string(data,payload+pointer)
  rows=list(db.execute('select * from files where layer=? and name=?',('Persistent','Data/Bundles/Windows/'+name)));assert len(rows)==1
  if name in done:continue
  done.add(name);packed=read_payload(rows[0]);nodes=read_bundle(packed,cipher)
  record={'path':actual,'bundle':name,'sha256':hashlib.sha256(packed).hexdigest(),'objects':[]}
  for cab,blob in nodes:
   if '.resS' in cab:continue
   for o in tree_objects(blob):
    if o['class_id'] not in [114,74,49,1,4]:continue
    fn=Path(actual).stem+'_'+str(o['path_id'])
    try:
     value=read_object(o)
     with (OUT/(fn+'.json')).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2,default=encode)
     record['objects'].append({'class':o['class_id'],'name':value.get('m_Name'),'file':fn+'.json','keys':list(value)})
    except ValueError as error:
     with (OUT/(fn+'.bin')).open('xb') as f:f.write(o['data'])
     record['objects'].append({'class':o['class_id'],'file':fn+'.bin','parse_error':str(error),'tree':o['tree']})
  report.append(record);print(actual,[(x['class'],x.get('name'),x.get('keys')) for x in record['objects']])
finally:codec.close();cipher.close();db.close()
with (OUT/'source-manifest.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2)
print('resolved selected',len(report),'of',len(terms))
