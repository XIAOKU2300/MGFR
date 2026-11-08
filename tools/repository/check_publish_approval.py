"""Local pre-push guard: explicit approval must match the exact SHA and private URL."""
from pathlib import Path
import json
import subprocess
import sys

def check(args,lines,approval,head):
    if len(args)<2 or args[1] not in {'https://github.com/XIAOKU2300/MGFR-private.git','git@github.com:XIAOKU2300/MGFR-private.git'}:return False
    if approval.get('repository')!='XIAOKU2300/MGFR-private' or approval.get('visibility')!='private' or approval.get('userApproved') is not True:return False
    if approval.get('commit')!=head or not approval.get('userInstruction'):return False
    for line in lines:
        fields=line.split()
        if len(fields)!=4:return False
        local_ref,local_sha,remote_ref,remote_sha=fields
        if local_sha!=head or remote_ref!='refs/heads/main' or local_ref!='refs/heads/main':return False
    return bool(lines)

def main():
    root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
    gitdir=Path(subprocess.check_output(['git','rev-parse','--git-dir'],cwd=root,text=True).strip())
    if not gitdir.is_absolute():gitdir=root/gitdir
    try:approval=json.loads((gitdir/'mgfr-publish-approval.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):approval={}
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    if not check(sys.argv[1:],sys.stdin.read().splitlines(),approval,head):
        print('Upload blocked: ask the user to approve this exact final commit and private repository. Do not reuse old approval.',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
