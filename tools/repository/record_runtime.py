"""Record source/resource fingerprints only; never copy local assets or settings."""
from pathlib import Path
import datetime
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]

def record(p):
    raw=p.read_bytes()
    return {'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def main():
    final=ROOT/'DialogueRenderRepair-20261020/Final-v3'
    audit=final/'IntegrationAudit-20261020/FootSourceCheck-20261021'
    receipt=json.loads((audit/'applied-receipt.json').read_text(encoding='utf-8-sig'))
    feet=json.loads((audit/'all-native-channels.json').read_text(encoding='utf-8-sig'))
    installed=[]
    for entry in receipt['entries']:
        item=record(Path(entry['path']))
        assert item['sha256']==entry['afterSha256'],'Installed resource differs from accepted recovery'
        installed.append(item)
    motions=ROOT/'SiLLMBridge-20261020/MainData/motions'
    clips=json.loads((motions/'manifest.json').read_text(encoding='utf-8-sig'))['clips']
    native=[]
    for clip in clips:
        item=record(motions/clip['file'])
        item.update({k:clip[k] for k in ('name','source_name','duration','frames','fps','loop') if k in clip})
        native.append(item)
    sources=[]
    for folder in [final/'Source',final/'Voice',ROOT/'DialogueMemory-20261020/src_v3']:
        for p in sorted(folder.rglob('*')):
            if p.is_file() and p.suffix in {'.py','.cs','.ps1','.cmd','.md'} and '__pycache__' not in p.parts:sources.append(record(p))
    launch=[ROOT/'启动MGFR.cmd',ROOT/'DialogueRenderRepair-20261020/launch_final.py',ROOT/'DialogueMemory-20261020/launch_memory.py']
    acceptance=ROOT/'DialogueRenderRepair-20261020/acceptance-Final-v3-20261021-082525-988188/Results/result.json'
    result=json.loads(acceptance.read_text(encoding='utf-8-sig'))
    assert result['pass'] and len(installed)==166 and len(native)==83
    report={
        'recordedAt':datetime.datetime.now().astimezone().isoformat(),
        'scope':'Source backup with local resource fingerprints, not a runnable asset distribution. No private configuration values included.',
        'entryChain':[record(p) for p in launch],
        'activePlayer':record(final/'Player/MGFR.exe'),
        'activeModule':record(final/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'),
        'canonicalSources':sources,
        'localNativeMotions':native,'localInstalledPoses':installed,
        'footRecovery':{'applied':receipt['applied'],'allOtherChannelsByteIdentical':feet['allOtherChannelsByteIdentical'],
            'allClipsNativeFootDelta':feet['allClipsNativeFootDelta'],'sampleFrames':sum(c['frames'] for c in feet['clips']),
            'maxErrorDegrees':max(c['nativeFootMaxErrorDegrees'] for c in feet['clips']),
            'evidence':[record(audit/'applied-receipt.json'),record(audit/'all-native-channels.json')]},
        'desktopAcceptance':{'result':record(acceptance),'passed':result['pass'],
            'frames':sum(p['frames'] for p in result['phases']),
            'abnormalJumps':sum(p['abnormalJumps'] for p in result['phases']),
            'headsetWornAcceptance':False},
        'excluded':'Local models, textures, animation binaries, voices, Unity installation, built players, real configuration, credentials, personal memory and conversation data.'}
    destination=ROOT/'docs/current-runtime-manifest.json'
    with destination.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'file':str(destination),'canonicalSources':len(sources),'nativeMotions':len(native),'installedPoses':len(installed),'desktopFrames':report['desktopAcceptance']['frames']},ensure_ascii=False))

if __name__=='__main__':main()
