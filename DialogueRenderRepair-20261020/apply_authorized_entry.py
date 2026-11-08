"""Apply one human-approved file at a time, verifying original, backup and candidate."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
ALLOWED={
    'launcher':ROOT/'启动MGFR.cmd',
    'navigation':ROOT/'项目入口说明.md',
    'test_motion':ROOT/'测试入口/01-动作连续性.cmd',
    'test_catalog':ROOT/'测试入口/02-全部可用动作.cmd',
    'test_dialogue':ROOT/'测试入口/03-语音与LLM动作联调.cmd',
    'test_readme':ROOT/'测试入口/说明.md',
}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--target',choices=list(ALLOWED)+['new_material','new_scale'],required=True);parser.add_argument('--apply-approved',action='store_true');args=parser.parse_args()
    manifest=json.loads((HERE/'Activation/manifest.json').read_text(encoding='utf-8'))
    if args.target.startswith('new_'):
        name='05-透明材质检查.cmd' if args.target=='new_material' else '06-衣物缩放检查.cmd'
        target=ROOT/'测试入口'/name
        item=next(x for x in manifest['newItems'] if Path(x['target'])==target)
        if target.exists():raise RuntimeError('Expected new target already exists')
    else:
        target=ALLOWED[args.target]
        item=next(x for x in manifest['items'] if x['group']==args.target)
        if Path(item['target'])!=target:raise RuntimeError('Target scope mismatch')
        if digest(target)!=item['beforeSha256']:raise RuntimeError('Target changed since review')
        if digest(Path(item['backup']))!=item['beforeSha256']:raise RuntimeError('Backup changed since review')
    candidate=Path(item['candidate'])
    if digest(candidate)!=item['candidateSha256']:raise RuntimeError('Candidate changed since review')
    if not args.apply_approved:
        print('REVIEW_VERIFIED',str(target));return
    with target.open('xb' if args.target.startswith('new_') else 'wb') as stream:stream.write(candidate.read_bytes())
    if digest(target)!=item['candidateSha256']:raise RuntimeError('Applied file verification failed')
    receipt=HERE/'Activation'/('applied-'+args.target+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    with receipt.open('x',encoding='utf-8') as stream:json.dump({'target':str(target),'candidateSha256':item['candidateSha256'],'backup':item.get('backup'),'userApproval':'同意，启用本次修复并更新入口'},stream,ensure_ascii=False,indent=2)
    print('APPLIED_VERIFIED',str(target))
if __name__=='__main__':main()
