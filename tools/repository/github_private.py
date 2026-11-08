"""Use existing GCM auth in memory for the explicitly requested private baseline."""
from pathlib import Path
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OWNER='XIAOKU2300'
NAME='MGFR-private'

def credential():
    env=dict(os.environ,GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
    result=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\nusername='+OWNER+'\n\n',text=True,capture_output=True,env=env,timeout=25)
    values=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode or not values.get('password'):raise RuntimeError('Existing GitHub login unavailable; no credential was printed.')
    return values['password']

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def main():
    assert sys.argv[1:]==['--create-requested-private-baseline']
    token=credential()
    opener=urllib.request.build_opener(NoRedirect)
    def request(path,payload=None):
        assert path.startswith('/') and not path.startswith('//')
        req=urllib.request.Request('https://api.github.com'+path,data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'MGFR-private-baseline','X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json'})
        try:
            with opener.open(req,timeout=30) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code==404:return None
            raise RuntimeError('GitHub operation failed with HTTP '+str(error.code)+'; response body suppressed.') from None
        except OSError:raise RuntimeError('GitHub transport failed; sensitive details suppressed.') from None
    user=request('/user');assert user and user['login'].lower()==OWNER.lower()
    repo=request('/repos/'+OWNER+'/'+NAME)
    created=False
    if repo is None:
        repo=request('/user/repos',{'name':NAME,'private':True,'auto_init':False,'description':'MGFR current source baseline and reviewed LLM update requirements; personal private repository.'});created=True
    assert repo and repo['private'] and repo['visibility']=='private' and repo['owner']['login'].lower()==OWNER.lower() and not repo['archived']
    print(json.dumps({'repository':repo['full_name'],'url':repo['html_url'],'private':repo['private'],'created':created,'defaultBranch':repo['default_branch']},ensure_ascii=False))

if __name__=='__main__':main()
