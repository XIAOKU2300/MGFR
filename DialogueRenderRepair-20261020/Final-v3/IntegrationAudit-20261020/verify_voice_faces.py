"""Exercise the real local HTTP handler, using an isolated bridge instance."""
from pathlib import Path
import json
import sys
import threading
from urllib.request import ProxyHandler,build_opener,Request

ROOT=Path('H:/MGFR')
sys.path.insert(0,str(ROOT/'SiLLMBridge-20261020'))
from main_bridge_final import make_server

def main():
    catalog=json.loads((ROOT/'SiLLMBridge-20261020/MainData/catalog.json').read_text(encoding='utf-8'))
    server=make_server(catalog,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    opener=build_opener(ProxyHandler({}));base='http://127.0.0.1:'+str(server.server_port)
    rows=[]
    try:
        for round_id,emotion in enumerate([e['name'] for e in catalog['emotions']],1):
            envelope={'round':round_id,'plan':{'version':1,'text':'面部协议回放。','emotion':emotion,'expression':'native','actions':[]}}
            request=Request(base+'/v1/voice/perform',data=json.dumps(envelope).encode('utf-8'),headers={'Content-Type':'application/json'})
            result=json.load(opener.open(request,timeout=3))['effective_plan']
            assert result['expression']=='auto' and result['expression_variant']!='native' and result['emotion']==emotion
            current=json.load(opener.open(base+'/v1/player/plan',timeout=3))
            assert current['voice_round']==round_id and current['expression_variant']==result['expression_variant']
            rows.append({'emotion':emotion,'variant':result['expression_variant'],'roundMatches':True})
        # Direct generic callers can still explicitly disable the face overlay.
        generic={'version':1,'text':'通用接口回放。','emotion':'neutral','expression':'native','actions':[]}
        request=Request(base+'/v1/perform',data=json.dumps(generic).encode('utf-8'),headers={'Content-Type':'application/json'})
        assert json.load(opener.open(request,timeout=3))['effective_plan']['expression_variant']=='native'
    finally:server.shutdown();server.server_close();thread.join(timeout=3)
    result={'pass':True,'emotions':rows,'genericExplicitNativePreserved':True,'externalCalls':False}
    out=Path(__file__).resolve().parent/'voice-face-result.json'
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':True,'emotions':len(rows),'result':str(out)},ensure_ascii=False))

if __name__=='__main__':main()
