"""Local memory management. Authentication is read from the local data folder, never printed."""
from pathlib import Path
import argparse
import json
import uuid
from urllib.request import Request,build_opener,ProxyHandler

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description='MGFR 记忆管理；服务启动后可用')
    parser.add_argument('operation',choices=['list','search','remember','forget','reload-knowledge'])
    parser.add_argument('value',nargs='?',default='')
    args=parser.parse_args()
    token=(HERE/'Data/local-auth.token').read_text(encoding='ascii').strip()
    base='http://127.0.0.1:18780'
    path='/memories';payload=None
    if args.operation=='search':path='/context';payload={'text':args.value}
    if args.operation=='remember':path='/turns';payload={'event_id':'manual-'+uuid.uuid4().hex,'text':args.value}
    if args.operation=='forget':path='/memories/forget';payload={'memory_id':args.value}
    if args.operation=='reload-knowledge':path='/knowledge/reload';payload={}
    request=Request(base+path,data=json.dumps(payload,ensure_ascii=False).encode('utf-8') if payload is not None else None,
                    headers={'Content-Type':'application/json','X-MGFR-Memory-Key':token})
    with build_opener(ProxyHandler({})).open(request,timeout=3) as response:
        print(json.dumps(json.load(response),ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('记忆管理未完成：'+type(error).__name__+'。请先启动MGFR。')
        raise SystemExit(1)
