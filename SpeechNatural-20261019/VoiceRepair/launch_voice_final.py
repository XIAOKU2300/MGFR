"""Boot the existing real voice service before the complete unified player.

No model downloads, credential copying, audio-device changes or service resets.
The credential is read only by the original installed voice_server.py.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[2]
DELIVERY=ROOT/'SpeechNatural-20261019'
PYTHON=ROOT/'dialogue-service/.venv/Scripts/python.exe'
SERVICE=DELIVERY/'VoiceService6'
EXPECTED_CONFIG=ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml'
PLAYER=ROOT/'HandCoexist-20261019/Project/Build/Windows/MGFR.exe'
HEALTH='http://127.0.0.1:8773/health'
EXPECTED={'vad':'silero','asr':'sensevoice','llm':'openai','tts':'gptsovits'}
OPENER=urllib.request.build_opener(urllib.request.ProxyHandler({}))

class VoiceStartupError(RuntimeError):
    pass

def read_health():
    try:
        with OPENER.open(HEALTH,timeout=2) as response:return json.load(response)
    except urllib.error.HTTPError:
        raise VoiceStartupError('The voice port responded with an error; its owner was left running.') from None
    except (urllib.error.URLError,TimeoutError,ConnectionError):return None

def verify_health(health):
    if health.get('status')!='ok':
        raise VoiceStartupError('Real voice engines are not ready; the game was not launched.')
    if health.get('engines')!=EXPECTED:
        raise VoiceStartupError('Voice engine configuration differs; the existing service was left running.')
    if health.get('speechRevision')!='natural-phrases-v2':
        raise VoiceStartupError('The voice port belongs to another speech revision; no service was stopped.')
    actual=health.get('configSource')
    if not actual or Path(actual).resolve()!=EXPECTED_CONFIG.resolve():
        raise VoiceStartupError('Voice port belongs to a different configuration; no process was stopped.')

def ensure_service():
    health=read_health()
    if health is not None:
        verify_health(health);return False
    if not PYTHON.is_file() or not (SERVICE/'voice_server.py').is_file():
        raise VoiceStartupError('The installed voice runtime or server script is missing.')
    env=os.environ.copy();env['PYTHONUTF8']='1';env['NO_PROXY']='127.0.0.1,localhost'
    log=DELIVERY/'VoiceRepair'/('voice-service-'+uuid.uuid4().hex+'.log')
    with log.open('xb') as stream:
        child=subprocess.Popen([str(PYTHON),'-X','utf8',str(SERVICE/'voice_server.py')],cwd=SERVICE,
            env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
        health=read_health()
        if health is not None:
            verify_health(health);return True
        if child.poll() is not None:
            raise VoiceStartupError('The voice service exited during startup. Diagnostic log: '+str(log))
        time.sleep(.25)
    raise VoiceStartupError('Voice startup exceeded 40 seconds. Diagnostic log: '+str(log))

def main():
    started=ensure_service()
    print('Voice ready: Silero + SenseVoice + configured LLM + current GPT-SoVITS voice.',flush=True)
    print('Voice service: '+('started' if started else 'reused')+' on 127.0.0.1:8773.',flush=True)
    if '--service-only' in sys.argv:return
    try:
        with OPENER.open('http://127.0.0.1:9880/voice_info',timeout=4) as response:json.load(response)
    except (urllib.error.URLError,TimeoutError,ValueError):
        raise VoiceStartupError('The current GPT-SoVITS voice service is unavailable; no voice model was changed.') from None
    if not PLAYER.is_file():raise VoiceStartupError('The unified player is missing.')
    log=DELIVERY/('headset-'+uuid.uuid4().hex+'.log')
    args=[str(PLAYER),'-mgfr-service-url','ws://127.0.0.1:8773/ws',
        '-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-mr-clean-edge',
        '-mgfr-wardrobe','-mgfr-shoes','-logFile',str(log)]
    subprocess.Popen(args,cwd=PLAYER.parent)
    print('Unified headset player started. F4 mutes the microphone.',flush=True)

if __name__=='__main__':
    try:main()
    except VoiceStartupError as error:
        print('MGFR voice startup: '+str(error),file=sys.stderr);sys.exit(1)
    except Exception as error:
        # Do not echo arbitrary upstream exceptions that may include credentials.
        print('MGFR voice startup failed ('+type(error).__name__+').',file=sys.stderr);sys.exit(1)
