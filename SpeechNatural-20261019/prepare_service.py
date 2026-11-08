from pathlib import Path
import ast

lab=Path(__file__).resolve().parent
root=lab.parent
folder=lab/'VoiceRepair';folder.mkdir()
s=(root/'HandCoexist-20261019/VoiceRepair/launch_unified.py').read_text(encoding='utf-8')
def once(a,b):
    global s
    assert s.count(a)==1,a
    s=s.replace(a,b)
once("DELIVERY=ROOT/'HandCoexist-20261019'","DELIVERY=ROOT/'SpeechNatural-20261019'")
once("SERVICE=ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService'","SERVICE=DELIVERY/'VoiceService5'\nEXPECTED_CONFIG=ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml'")
once("PLAYER=DELIVERY/'Project/Build/Windows/MGFR.exe'","PLAYER=ROOT/'HandCoexist-20261019/Project/Build/Windows/MGFR.exe'")
s=s.replace('127.0.0.1:8772','127.0.0.1:8773')
once("(SERVICE/'voice.toml').resolve()","EXPECTED_CONFIG.resolve()")
once("    actual=health.get('configSource')", "    if health.get('speechRevision')!='natural-phrases-v1':\n        raise VoiceStartupError('The voice port belongs to another speech revision; no service was stopped.')\n    actual=health.get('configSource')")
ast.parse(s)
with (folder/'launch_unified.py').open('x',encoding='utf-8') as output:output.write(s)
print(folder/'launch_unified.py')
