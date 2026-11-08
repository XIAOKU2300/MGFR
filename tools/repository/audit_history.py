"""Check reachable history without printing blob contents or credentials."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('snapshot',Path(__file__).with_name('prepare_snapshot.py'))
snapshot=importlib.util.module_from_spec(spec);spec.loader.exec_module(snapshot)
objects={}
for line in subprocess.check_output(['git','rev-list','--objects','HEAD'],cwd=ROOT).decode('utf-8').splitlines():
    sha,_,path=line.partition(' ');objects[sha]=path
check=subprocess.run(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],input='\n'.join(objects)+'\n',text=True,capture_output=True,cwd=ROOT,check=True)
blobs=[]
for line in check.stdout.splitlines():
    sha,kind,size=line.split()
    if kind=='blob':blobs.append((sha,objects[sha],int(size)))
bad=[]
for sha,path,size in blobs:
    if re.search(r'(?i)(?:\.(?:pmx|pmd|vmd|vpd|fbx|blend\d*|ckpt|pth|onnx|wav|mp3|flac|m4a|exe|dll|zip|bin|motion|hpose)$|(?:^|/)(?:textures|other tex|data|models)/|(?:^|/)(?:config|voice)\.toml$|(?:^|/)\.env(?:\.|$))',path):
        bad.append({'path':path,'sha':sha,'kind':'excluded-resource-in-history'});continue
    raw=subprocess.check_output(['git','cat-file','blob',sha],cwd=ROOT)
    try:text=raw.decode('utf-8-sig')
    except UnicodeError:bad.append({'path':path,'sha':sha,'kind':'binary-history-blob'});continue
    hits=snapshot.secret_hits(text)
    if hits:bad.append({'path':path,'sha':sha,'findings':hits})
print(json.dumps({'objects':len(objects),'blobs':len(blobs),'blobBytes':sum(b[2] for b in blobs),'largest':[{'path':p,'bytes':n} for s,p,n in sorted(blobs,key=lambda v:v[2],reverse=True)[:5]],'issues':bad},ensure_ascii=False,indent=2))
