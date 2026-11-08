"""Read-only inventory plus recoverable copies. Does not remove any launcher."""
from pathlib import Path
import hashlib,json

lab=Path(__file__).resolve().parent;root=lab.parent
targets=sorted((p for p in root.iterdir() if p.is_file() and p.name.startswith('启动MGFR') and p.suffix.lower()=='.cmd' and p.name!='启动MGFR.cmd'),key=lambda p:p.name)
backup=lab/'LauncherBackup';backup.mkdir()
entries=[]
for path in targets:
    assert path.resolve().parent==root.resolve()
    data=path.read_bytes();copy=backup/(path.name+'.bak')
    with copy.open('xb') as f:f.write(data)
    entries.append({'path':str(path),'backup':str(copy),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
manifest={'operation':'PENDING_USER_CONFIRMATION_NO_FILES_REMOVED','root':str(root),'count':len(entries),
          'keep':str(root/'启动MGFR.cmd'),'targets':entries}
with (lab/'launcher-cleanup.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2,ensure_ascii=False)
lines=['# 待确认的旧入口清单','',f'数量：{len(entries)} 个文件。这里只列项目根目录的旧启动脚本，不删除程序、源码或资源。',
       '',f'最终保留：`{root / "启动MGFR.cmd"}`。',f'逐文件原件备份：`{backup}`，已核对 SHA-256。','']
lines += [str(i+1)+'. `'+item['path']+'`' for i,item in enumerate(entries)]
with (lab/'旧入口删除清单.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
print('COUNT='+str(len(entries)))
for item in entries:print(item['path'])
print('BACKUP='+str(backup))
print('No launcher removed; awaiting explicit confirmation.')
