from pathlib import Path
import hashlib,json,uuid,urllib.request,difflib

ROOT=Path(__file__).resolve().parent.parent
LAB=ROOT/'SpeechNatural-20261019'
entry=ROOT/'启动MGFR.cmd'
expected='8f1ae6d052fde21f59d6b3c85b5e12a934b57e675dda9ddd3548468982b841bc'
sha=lambda data:hashlib.sha256(data).hexdigest()
old=entry.read_bytes()
assert sha(old)==expected,'Entry changed; no overwrite performed'
assert json.loads((LAB/'accepted-validation.json').read_text(encoding='utf-8'))['passed']
player=ROOT/'HandCoexist-20261019/Project/Build/Windows/MGFR.exe'
assert player.is_file()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8773/health',timeout=5) as response:health=json.load(response)
assert health['status']=='ok' and health['speechRevision']=='natural-phrases-v6'
assert health['engines']=={'vad':'silero','asr':'sensevoice','llm':'openai','tts':'gptsovits'}
backup_dir=LAB/'LauncherBackup';backup_dir.mkdir(exist_ok=True)
backup=backup_dir/('启动MGFR-'+uuid.uuid4().hex+'.cmd.bak')
with backup.open('xb') as stream:stream.write(old)
assert backup.read_bytes()==old
new=('\r\n'.join(['@echo off',
     '"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -X utf8 "H:\\MGFR\\SpeechNatural-20261019\\VoiceRepair\\launch_voice_v6.py"',
     'if errorlevel 1 pause',''])).encode('utf-8')
candidate=LAB/'启动MGFR.cmd.approved'
with candidate.open('xb') as stream:stream.write(new)
# User explicitly authorized this single existing-file replacement this turn.
assert sha(entry.read_bytes())==expected
entry.write_bytes(new)
assert entry.read_bytes()==new
entries=list(ROOT.glob('启动MGFR*.cmd'));assert entries==[entry]
original=ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService'
before=json.loads((LAB/'base-hashes.json').read_text(encoding='utf-8'))
unchanged={name:sha((original/name).read_bytes())==digest for name,digest in before.items()}
changes=[]
for relative in ('app/text.py','app/pipeline.py','app/engines/tts_gptsovits.py','app/engines/llm_openai.py','app/engines/factory.py','app/main.py','app/speech_style.py','app/speech_pcm.py','app/speech_verify.py'):
    source=original/relative;target=LAB/'VoiceService10'/relative
    previous=source.read_text(encoding='utf-8').splitlines(True) if source.exists() else []
    changes.extend(difflib.unified_diff(previous,target.read_text(encoding='utf-8').splitlines(True),fromfile='original/'+relative,tofile='optimized/'+relative))
with (LAB/'complete-speech-adaptation.patch').open('x',encoding='utf-8') as stream:stream.writelines(changes)
receipt={'activated':True,'entry':str(entry),'entrySha256':sha(new),'previousEntrySha256':expected,
         'backup':str(backup),'backupVerified':True,'entryCount':1,'player':str(player),
         'voiceService':str(LAB/'VoiceService10'),'speechRevision':health['speechRevision'],
         'unitTestsPassed':25,'audioValidationPassed':True,'originalSourceHashChecks':unchanged,
         'userMicrophoneUsed':False,'gameRestarted':False,'speechQuality':health.get('speechQuality')}
with (LAB/'activation-receipt.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,ensure_ascii=False,indent=2)
print(json.dumps({'activated':True,'entry':str(entry),'backup':str(backup),'testsPassed':25,'audioSamplesPassed':4,'originalSourcesUnchanged':all(unchanged.values())},ensure_ascii=False))
