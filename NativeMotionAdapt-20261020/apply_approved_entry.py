"""Apply ONE previously reviewed entry group, with unchanged-target checks and backups."""
from pathlib import Path
import argparse
import hashlib
import json
import datetime
ROOT=Path(__file__).resolve().parent
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--target',required=True,choices=['launcher','navigation','tests']);parser.add_argument('--apply-approved',action='store_true');args=parser.parse_args()
    manifest=json.loads((ROOT/'Activation/manifest.json').read_text(encoding='utf-8'));items=[x for x in manifest['items'] if x['group']==args.target]
    for item in items:
        target=Path(item['target']);backup=Path(item['backup']);candidate=Path(item['candidate'])
        if hashlib.sha256(target.read_bytes()).hexdigest()!=item['beforeSha256']:raise RuntimeError('Target changed since review: '+str(target))
        if hashlib.sha256(backup.read_bytes()).hexdigest()!=item['beforeSha256']:raise RuntimeError('Backup contract failed')
        if hashlib.sha256(candidate.read_bytes()).hexdigest()!=item['candidateSha256']:raise RuntimeError('Candidate changed since review')
    if not args.apply_approved:
        print(json.dumps({'mode':'read-only review','group':args.target,'targets':[x['target'] for x in items],'count':len(items),'backupsVerified':True},ensure_ascii=False,indent=2));return
    for item in items:
        target=Path(item['target']);candidate=Path(item['candidate'])
        with target.open('wb') as f:f.write(candidate.read_bytes())
        if hashlib.sha256(target.read_bytes()).hexdigest()!=item['candidateSha256']:raise RuntimeError('Applied file verification failed')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    with (ROOT/'Activation'/('applied-'+args.target+'-'+stamp+'.json')).open('x',encoding='utf-8') as f:json.dump({'group':args.target,'applied':items},f,ensure_ascii=False,indent=2)
    print('APPLIED_VERIFIED',args.target,len(items))
if __name__=='__main__':main()
