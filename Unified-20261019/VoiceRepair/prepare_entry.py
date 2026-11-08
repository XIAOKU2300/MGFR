from pathlib import Path
import hashlib,json,difflib

folder=Path(__file__).resolve().parent;entry=folder.parents[1]/'启动MGFR.cmd'
data=entry.read_bytes()
with (folder/'启动MGFR.cmd.original.bak').open('xb') as f:f.write(data)
candidate='\r\n'.join(['@echo off',
 '"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -X utf8 "H:\\MGFR\\Unified-20261019\\VoiceRepair\\launch_unified.py"',
 'if errorlevel 1 pause',''])
with (folder/'启动MGFR.cmd.pending').open('x',encoding='ascii',newline='') as f:f.write(candidate)
with (folder/'entry.patch').open('x',encoding='utf-8') as f:
    f.writelines(difflib.unified_diff(data.decode('ascii').splitlines(True),candidate.splitlines(True),fromfile=str(entry),tofile=str(entry)))
with (folder/'entry-change.json').open('x',encoding='utf-8') as f:
    json.dump({'target':str(entry),'originalSha256':hashlib.sha256(data).hexdigest(),
               'backup':str(folder/'启动MGFR.cmd.original.bak'),
               'candidate':str(folder/'启动MGFR.cmd.pending'),
               'state':'PREPARED_PENDING_USER_OVERWRITE_CONFIRMATION'},f,indent=2,ensure_ascii=False)
print('Prepared one-file launcher change and backup; existing entry untouched.')
