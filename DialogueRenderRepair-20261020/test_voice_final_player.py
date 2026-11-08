"""Test the installed JSON voice adapter and real Unity PCM path using local fixtures."""
from pathlib import Path
import argparse
import datetime
import json
import os
import socket
import subprocess
import sys
import threading
import time
from urllib.request import build_opener, ProxyHandler

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent

def worker(ready):
    sys.path.insert(0,str(PROJECT/'SpeechNatural-20261019/VoiceService10'))
    sys.path.insert(0,str(PROJECT/'SpeechNatural-20261019/VoiceRepair'))
    from app import main as voice_main
    from app.config import Config
    from app.engines.factory import Engines
    from app.engines.stub import EnergyVad, StubAsr, StubLlm, StubTts
    plan={'version':1,'text':'我有一点难过，不过会陪你慢慢说。','emotion':'sad','emotion_intensity':.6,'actions':[{'name':'think','at':0}]}
    def build(_cfg):
        return Engines(vad=EnergyVad(),asr=StubAsr(),llm=StubLlm(reply=json.dumps(plan,ensure_ascii=False),first_token_delay_s=.05,token_delay_s=.001),tts=StubTts(realtime=True))
    voice_main.build_all=build
    app=voice_main.create_app(Config())
    sys.path.insert(0,str(ROOT/'Final-v3/Voice'))
    import install_voice_v4
    install_voice_v4.install(app,'http://127.0.0.1:1')
    sys.path.append(str(PROJECT/'SiLLMBridge-20261020'))
    from main_bridge_final import make_server
    catalog=json.loads((PROJECT/'SiLLMBridge-20261020/MainData/catalog.json').read_text(encoding='utf-8'))
    bridge=make_server(catalog,0);threading.Thread(target=bridge.serve_forever,daemon=True).start()
    sys.modules['app.mgfr_avatar_json'].URL='http://127.0.0.1:'+str(bridge.server_port)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    ports={'voice':listener.getsockname()[1],'actions':bridge.server_port}
    with ready.open('x',encoding='utf-8') as f:json.dump(ports,f)
    import uvicorn
    try:uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False)).run(sockets=[listener])
    finally:bridge.shutdown();bridge.server_close();listener.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=Path);args=parser.parse_args()
    if args.worker:return worker(args.worker)
    output=ROOT/('unity-voice-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));output.mkdir();ready=output/'ports.json'
    children=[];handles=[];opener=build_opener(ProxyHandler({}))
    try:
        stream=(output/'fixtures.log').open('xb');handles.append(stream)
        child=subprocess.Popen([sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker',str(ready)],stdout=stream,stderr=stream,creationflags=subprocess.CREATE_NO_WINDOW);children.append(child)
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            if child.poll() is not None:raise RuntimeError('Local fixtures exited; see fixtures.log')
            if ready.exists():
                ports=json.loads(ready.read_text())
                try:
                    with opener.open('http://127.0.0.1:'+str(ports['voice'])+'/health',timeout=.3) as response:
                        if json.load(response).get('status')=='ok':break
                except OSError:pass
            time.sleep(.1)
        else:raise RuntimeError('Local fixture startup timed out')
        player=ROOT/'Final-v3/Player/MGFR.exe'
        cmd=[str(player),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-structured-voice','-mgfr-avatar-data',str(PROJECT/'SiLLMBridge-20261020/MainData'),
             '-mgfr-action-port',str(ports['actions']),'-mgfr-service-url','ws://127.0.0.1:'+str(ports['voice'])+'/ws',
             '-mgfr-actions-network-review','-mgfr-actions-network-out',str(output/'result.json'),'-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-logFile',str(output/'player.log')]
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        stream=(output/'startup.log').open('xb');handles.append(stream)
        child=subprocess.Popen(cmd,cwd=player.parent,stdout=stream,stderr=stream,startupinfo=startup);children.append(child)
        code=child.wait(timeout=65)
        result=json.loads((output/'result.json').read_text(encoding='utf-8-sig'))
        print(json.dumps({'exitCode':code,'result':result,'path':str(output/'result.json')},ensure_ascii=False,indent=2),flush=True)
        raise SystemExit(0 if code==0 and result['pass'] else 1)
    finally:
        for child in reversed(children):
            if child.poll() is None:child.terminate();child.wait(timeout=10)
        for stream in handles:stream.close()
if __name__=='__main__':main()
