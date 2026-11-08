"""Use the existing voice bootstrap with the verified continuous-motion player."""
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys
import types
from urllib.request import build_opener, ProxyHandler

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
SOURCE=PROJECT/'SpeechNatural-20261019/VoiceRepair/launch_voice_v6.py'
PLAYER=ROOT/'Current/Player/MGFR.exe'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--desktop',action='store_true');args=parser.parse_args()
    if args.check:
        result={'playerExists':PLAYER.is_file(),'voiceBootstrapExists':SOURCE.is_file(),'avatarDataExists':(PROJECT/'SiLLMBridge-20261020/MainData/motions/manifest.json').is_file(),'mode':'read-only preflight; no microphone or model request'}
        opener=build_opener(ProxyHandler({}))
        for label,url in [('voice','http://127.0.0.1:8773/health'),('actions','http://127.0.0.1:18766/v1/catalog'),('tts','http://127.0.0.1:9880/voice_info')]:
            try:
                with opener.open(url,timeout=2) as response:
                    value=json.load(response)
                    result[label]={'available':True}
                    if label=='voice':result[label].update({key:value.get(key) for key in ['status','engines','speechRevision','avatarRevision']})
                    if label=='actions':result[label]['callable']=sum(x.get('callable',True) for x in value.get('actions',[]))
            except (OSError,ValueError):result[label]={'available':False}
        print(json.dumps(result,ensure_ascii=False,indent=2));return
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(SOURCE.parent))
    spec=importlib.util.spec_from_file_location('mgfr_installed_voice_launcher',SOURCE)
    installed=importlib.util.module_from_spec(spec);spec.loader.exec_module(installed)
    installed.PLAYER=PLAYER
    installed.DELIVERY=ROOT/'Logs';installed.DELIVERY.mkdir(exist_ok=True);(installed.DELIVERY/'VoiceRepair').mkdir(exist_ok=True)
    original_popen=subprocess.Popen
    def start(command,**kwargs):
        if command and Path(command[0])==PLAYER and args.desktop:command=list(command)+['-mgfr-noxr']
        return original_popen(command,**kwargs)
    installed.subprocess=types.SimpleNamespace(Popen=start,CREATE_NO_WINDOW=subprocess.CREATE_NO_WINDOW)
    installed.main()
if __name__=='__main__':
    try:main()
    except Exception as error:
        print('MGFR startup did not complete ('+type(error).__name__+'). Existing services were preserved.',file=sys.stderr)
        raise SystemExit(1)
