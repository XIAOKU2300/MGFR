"""Inventory a code-only upload without touching the running project or git index."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import os
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
SKIP={'unity hub','.git','.agents','.impeccable','.pi','converted','batch','work','adapted-skin',
      'library','temp','obj','logs','models','node_modules','__pycache__','.venv','venv','.vs','.idea',
      'player','reviewplayer','reviewplayer-v2','managed','monobleedingedge','plugins',
      'streamingassets','backups','backups-before-application','sourcebackup','data','tests-output',
      'third_party','third-party','textures','other tex','preview-v1','preview-v2','preview-v3','preview-v4','preview-v5','preview-v6'}
CODE={'.py','.cs','.shader','.compute','.hlsl','.cginc','.ps1','.cmd','.bat','.sh','.md','.uss','.uxml','.asmdef','.asmref'}
SETTINGS={'.asset','.unity','.inputactions','.controller','.overridecontroller'}
JSON_NAMES={'manifest.json','packages-lock.json','package.json','package-lock.json','sceneTemplates.json','scenetemplates.json'}
SAFE_ROOT={'README.md','DESIGN.md','PRODUCT.md','RENDER-DESIGN-20261018.md','项目入口说明.md','渲染与物理交付说明-20261018.md','启动MGFR.cmd','AGENTS.md','.gitignore','.gitattributes'}
EXPLICIT={'SiLLMBridge-20261020/MainData/catalog.json','SiLLMBridge-20261020/MainData/expressions.json','SiLLMBridge-20261020/MainData/motions/manifest.json','docs/current-runtime-manifest.json'}
REVIEWED_FIXTURES={'SiLLMBridge-20261020/client/test_llm_chat.py':
 ('d2f238bb2f3c27d929c24a80be07a09adf4e9ecc5c00232ff12409bfabf3e2ae',{77,116})}
PATTERNS=[('private-key',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
 ('token',re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,})')),
 ('secret-literal',re.compile(r'''(?i)["']?(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)["']?\s*[:=]\s*["']([^"'\r\n]{12,})["']''')),
 ('auth-header',re.compile(r'''(?i)["']authorization["']\s*:\s*["'](?:bearer|token)\s+([A-Za-z0-9_.-]{20,})["']'''))]
PLACEHOLDER=re.compile(r'(?i)example|placeholder|your[_ -]|replace|dummy|test|invalid|localhost|\{|\}|os\.environ|MGFR_|str\(|getenv')

def secret_hits(text):
    hits=[]
    for kind,pattern in PATTERNS:
        for match in pattern.finditer(text):
            value=match.group(1) if match.lastindex else match.group(0)
            if kind=='secret-literal' and PLACEHOLDER.search(value):continue
            hits.append({'kind':kind,'line':text.count('\n',0,match.start())+1})
    return hits

def allowed(path):
    rel=path.relative_to(ROOT);parts=rel.parts;name=path.name;low=name.lower()
    if len(parts)==1:return name in SAFE_ROOT
    if parts[0].lower()=='editor':return False
    if any(p.lower() in SKIP or p.startswith('【') for p in parts[:-1]):return False
    if any(p.lower().startswith(('acceptance-','candidate-','baseline-','review-','mainplayer','player-','previewproject','unityassets','shaderproject','unityproject','shaderbundle')) for p in parts[:-1]):return False
    if any('backup' in p.lower() or p.lower().startswith('applied-') for p in parts[:-1]):return False
    if 'packages' in [p.lower() for p in parts[:-1]]:return low in {'manifest.json','packages-lock.json'}
    if path.suffix.lower() in CODE:return True
    if path.suffix.lower() in SETTINGS:return 'ProjectSettings' in parts or ('Assets' in parts and name!='test1.unity')
    if path.suffix.lower()=='.json':return low in {v.lower() for v in JSON_NAMES} or 'ProjectSettings' in parts or rel.as_posix() in EXPLICIT
    if path.suffix.lower()=='.toml':return low in {'pyproject.toml','config.example.toml'} or low.endswith('.example.toml')
    if path.suffix.lower()=='.ini':return low in {'pytest.ini','tox.ini'}
    if path.suffix.lower()=='.txt':return low.startswith(('requirements','license','notice','copying')) or low in {'projectversion.txt','system.zh.txt'}
    if name.startswith(('LICENSE','NOTICE','COPYING')):return True
    return False

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)

def main():
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output=ROOT/'work/repository-upload'/stamp;output.mkdir(parents=True,exist_ok=False)
    paths=[]
    for directory,dirs,files in os.walk(ROOT):
        if Path(directory)==ROOT:dirs[:]=[d for d in dirs if d.lower()!='editor']
        dirs[:]=[d for d in dirs if d.lower() not in SKIP and not d.startswith('【') and not d.lower().startswith(('acceptance-','candidate-','baseline-','review-','mainplayer','player-','previewproject','unityassets','shaderproject','unityproject','shaderbundle')) and 'backup' not in d.lower() and not d.lower().startswith('applied-')]
        for name in files:
            p=Path(directory)/name
            if allowed(p):paths.append(p)
    tracked=[ROOT/s.decode('utf-8') for s in git('ls-files','-z').split(b'\0') if s]
    for p in tracked:
        if not p.is_file():raise RuntimeError('Tracked file missing: '+str(p.relative_to(ROOT)))
        if p.suffix.lower()!='.meta' and not allowed(p):raise RuntimeError('Tracked path needs review: '+str(p.relative_to(ROOT)))
        paths.append(p)
    # Keep meta files only for included source files/directories, never for omitted assets.
    selected=set(paths)
    for p in list(selected):
        for parent in [p,*[v for v in p.parents if v!=ROOT and v.is_relative_to(ROOT)]]:
            meta=Path(str(parent)+'.meta')
            if meta.is_file():selected.add(meta)
    hook=ROOT/'.githooks/pre-push'
    if hook.is_file():selected.add(hook)
    # Honor existing ignore rules without forcing ignored local files into Git.
    relative=b''.join(p.relative_to(ROOT).as_posix().encode('utf-8')+b'\0' for p in sorted(selected))
    ignored_result=subprocess.run(['git','check-ignore','--stdin','-z'],input=relative,cwd=ROOT,capture_output=True)
    if ignored_result.returncode not in (0,1):raise RuntimeError('Ignore-rule check failed')
    ignored={s.decode('utf-8') for s in ignored_result.stdout.split(b'\0') if s}
    selected={p for p in selected if p.relative_to(ROOT).as_posix() not in ignored}
    entries=[];issues=[];reviewed=[];totals=collections.Counter()
    for p in sorted(selected):
        raw=p.read_bytes()
        try:text=raw.decode('utf-8-sig')
        except UnicodeError:issues.append({'path':p.relative_to(ROOT).as_posix(),'kind':'non-utf8'});continue
        hits=secret_hits(text)
        reviewed_fixture=REVIEWED_FIXTURES.get(p.relative_to(ROOT).as_posix())
        if hits and reviewed_fixture and hashlib.sha256(raw).hexdigest()==reviewed_fixture[0] and all(x['kind']=='secret-literal' and x['line'] in reviewed_fixture[1] for x in hits):
            reviewed.append({'path':p.relative_to(ROOT).as_posix(),'reason':'Reviewed fixed dummy credentials in loopback fake-server tests; exact full-file fingerprint required.'});hits=[]
        if hits:issues.append({'path':p.relative_to(ROOT).as_posix(),'findings':hits});continue
        if len(raw)>5_000_000:issues.append({'path':p.relative_to(ROOT).as_posix(),'kind':'large-text','bytes':len(raw)});continue
        rel=p.relative_to(ROOT).as_posix();entries.append({'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});totals[rel.split('/')[0]]+=1
    result={'root':str(ROOT),'head':git('rev-parse','HEAD').decode().strip(),'files':len(entries),'bytes':sum(e['bytes'] for e in entries),'entries':entries,'issues':issues,'reviewedFixtures':reviewed,'ignoredByExistingRules':len(ignored),'byRoot':dict(totals)}
    with (output/'inventory.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    with (output/'paths.nul').open('xb') as f:f.write(b''.join(e['path'].encode('utf-8')+b'\0' for e in entries))
    print(json.dumps({'output':str(output),'files':result['files'],'bytes':result['bytes'],'byRoot':result['byRoot'],'issues':issues},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
