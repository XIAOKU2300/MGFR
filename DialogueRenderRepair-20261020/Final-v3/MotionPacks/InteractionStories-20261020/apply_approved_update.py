"""Apply the five concrete motion-only updates explicitly approved by the user."""
from pathlib import Path
import ast, datetime, hashlib, json, os, re, uuid
ROOT=Path('H:/MGFR');PACK=Path(__file__).resolve().parent
RELEASE=ROOT/'DialogueRenderRepair-20261020/Final-v3'
MAIN=ROOT/'SiLLMBridge-20261020/MainData'
EXPECTED=[MAIN/'motions/manifest.json',MAIN/'expressions.json',MAIN/'catalog.json',RELEASE/'Voice/avatar_json_v2.py',ROOT/'DialogueRenderRepair-20261020/launch_final.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 review=json.loads((PACK/'InstallReview/overwrite-review.json').read_text(encoding='utf-8'))
 assert [Path(c['target']) for c in review['changes']]==EXPECTED
 for c in review['changes']:
  assert sha(Path(c['target']))==c['before_sha256'], 'Active target changed; refusing stale replacement'
  assert sha(Path(c['backup']))==c['before_sha256'], 'Backup mismatch'
  assert sha(Path(c['candidate']))==c['after_sha256'], 'Candidate mismatch'
 for name,digest in review['immutable'].items():assert sha(Path(name))==digest, 'Runtime/entry changed'
 for c in review['changes'][3:]:ast.parse(Path(c['candidate']).read_text(encoding='utf-8'))
 manifest=json.loads((PACK/'Adapted/motions/manifest.json').read_text(encoding='utf-8'))
 files=[]
 for c in manifest['clips']:
  assert re.fullmatch('[a-z0-9_]+',c['name']) and c['file']==c['name']+'.motion'
  files.append((PACK/'Adapted/motions'/c['file'],MAIN/'motions'/c['file']))
  for skin in ['swimsuit','original']:
   files.append((PACK/'Adapted/native-actions'/skin/(c['name']+'.hpose'),RELEASE/'Player/MGFR_Data/StreamingAssets/native-actions'/skin/(c['name']+'.hpose')))
 assert len(files)==171 and len({d for _,d in files})==171
 for source,dest in files:
  assert source.is_file() and not dest.exists(), 'An additive target exists; refusing overwrite'
  assert dest.parent.is_dir()
 stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
 plan=PACK/('application-plan-'+stamp+'.json')
 with plan.open('x',encoding='utf-8') as f:json.dump(dict(approved_by_user='Explicit approval of these five updates and current worker reload in this conversation',new_files=[dict(source=str(s),target=str(d),sha256=sha(s)) for s,d in files],overwrites=review['changes']),f,ensure_ascii=False,indent=2)
 for source,dest in files:
  with dest.open('xb') as f:f.write(source.read_bytes())
  assert sha(dest)==sha(source)
 for c in review['changes']:
  target=Path(c['target']);temporary=target.parent/('.motion-update-'+uuid.uuid4().hex+'.tmp')
  with temporary.open('xb') as f:f.write(Path(c['candidate']).read_bytes());f.flush();os.fsync(f.fileno())
  assert sha(target)==c['before_sha256']
  os.replace(temporary,target)
  assert sha(target)==c['after_sha256']
  print('APPLIED',str(target),flush=True)
 for name,digest in review['immutable'].items():assert sha(Path(name))==digest
 with (PACK/('application-result-'+stamp+'.json')).open('x',encoding='utf-8') as f:json.dump(dict(status='APPLIED',new_files=171,overwritten_files=5,unchanged_runtime_and_entry=True,worker_reload='pending',plan=str(plan)),f,ensure_ascii=False,indent=2)
 print('Applied 171 new resources and 5 approved updates. Player DLL, root entry and models unchanged.',flush=True)
if __name__=='__main__':main()
