from pathlib import Path,PurePosixPath
import json,urllib.request,hashlib,io,tarfile
lab=Path('H:/MGFR/HandLab-20261018');dest=lab/'OfficialPackages';dest.mkdir()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({'https':'http://127.0.0.1:7890'}))
receipt=[]
for name,version in [('com.unity.xr.hands','1.8.1'),('com.unity.mathematics','1.2.6')]:
 if name=='com.unity.xr.hands':registry=json.loads((lab/'registry-hands.json').read_bytes())
 else:
  with opener.open('https://packages.unity.com/'+name,timeout=30) as r:registry=json.loads(r.read())
 info=registry['versions'][version]
 with opener.open(info['dist']['tarball'],timeout=50) as r:raw=r.read()
 actual=hashlib.sha1(raw).hexdigest();assert actual==info['dist']['shasum']
 target=dest/name;target.mkdir();count=0
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  for item in archive.getmembers():
   parts=PurePosixPath(item.name).parts
   assert parts[0]=='package' and '..' not in parts and not item.issym() and not item.islnk()
   path=target.joinpath(*parts[1:]);assert path.resolve().is_relative_to(target.resolve())
   if item.isdir():path.mkdir(parents=True,exist_ok=True)
   elif item.isfile():
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(archive.extractfile(item).read())
    count+=1
 receipt.append(dict(name=name,version=version,source=info['dist']['tarball'],sha1=actual,files=count))
 print(name,version,'verified archive',len(raw),'bytes,',count,'files')
with (lab/'official-package-receipt.json').open('x',encoding='utf8') as f:json.dump(receipt,f,indent=2)
