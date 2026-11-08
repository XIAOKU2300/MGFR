from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'H:/MGFR/work/si-animation-20261019')
from extract_verified import connect,read_payload
from bundle_reader import Helper,read_bundle
from managed_typetree_v2 import read_file
source=json.loads((ROOT/'face-sources-v1/source-manifest.json').read_text(encoding='utf-8'))
row=next(x for x in source if '/skeletalmorphcfg/' in x['path'])
db=connect();vfs=list(db.execute('select * from files where layer=? and name=?',('Persistent','Data/Bundles/Windows/'+row['bundle'])));db.close();assert len(vfs)==1
helper=Helper('OfflineDecoder.dll')
try:nodes=read_bundle(read_payload(vfs[0]),helper)
finally:helper.close()
for name,data in nodes:
 if '.resS' in name:continue
 objects,refs,externals,parse=read_file(data);print('reference types',[(k,[(n['name'],n['type']) for n in v['children']]) for k,v in refs.items()])
 for o in objects:
  if o['class_id']==114:
   value=parse(o)
   with (ROOT/'face-sources-v1/native-face-avatar-decoded.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False)
   print('fields',list(value),'data fields',list(value['data']),'references',len(value['references']['RefIds']))
