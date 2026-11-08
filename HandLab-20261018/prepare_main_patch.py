from pathlib import Path
import json,hashlib,difflib,shutil
root=Path('H:/MGFR');lab=root/'HandLab-20261018';main=root/'unity-client';project=lab/'Project-v3'
backup=lab/'OriginalFiles';prepared=lab/'PreparedFiles';backup.mkdir();prepared.mkdir()
relative=['Packages/packages-lock.json','Assets/XR/Settings/OpenXR Package Settings.asset'];manifest=[];diff=[]
for name in relative:
 target=main/name;src=project/name;old=target.read_bytes();new=src.read_bytes()
 for parent,data in [(backup,old),(prepared,new)]:
  p=parent/name;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(data)
 manifest.append(dict(path=str(target),backup=str(backup/name),prepared=str(prepared/name),before=hashlib.sha256(old).hexdigest(),after=hashlib.sha256(new).hexdigest()))
 diff.extend(difflib.unified_diff(old.decode('utf-8-sig').splitlines(True),new.decode('utf-8-sig').splitlines(True),fromfile=str(target),tofile=str(src)))
additions=[]
for folder in ['Assets/MGFR/Scripts/BareHands','Packages/com.unity.xr.hands','Packages/com.unity.mathematics']:
 additions += [(p,main/p.relative_to(project)) for p in (project/folder).rglob('*') if p.is_file()]
 if (project/(folder+'.meta')).exists():additions.append((project/(folder+'.meta'),main/(folder+'.meta')))
for name in ['Assets/MGFR/Resources/HandDepth.shader','Assets/MGFR/Resources/HandDepth.shader.meta','Assets/MGFR/Editor/HandsBuild.cs','Assets/MGFR/Editor/HandsBuild.cs.meta']:
 additions.append((project/name,main/name))
assert all(not dst.exists() for _,dst in additions)
with (lab/'main-overwrite-manifest.json').open('x',encoding='utf8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
with (lab/'main-additions-manifest.json').open('x',encoding='utf8') as f:json.dump([dict(source=str(s),target=str(d),sha256=hashlib.sha256(s.read_bytes()).hexdigest()) for s,d in additions],f,ensure_ascii=False,indent=2)
with (lab/'main-configuration.patch').open('x',encoding='utf8') as f:f.writelines(diff)
print('Existing-file replacements:',len(manifest),'new files:',len(additions))
print('Configuration diff lines:',len(diff))
for p in manifest:print(p['path'])
