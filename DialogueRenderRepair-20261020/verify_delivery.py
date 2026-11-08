"""Read-only verification plus a new immutable delivery receipt."""
from pathlib import Path
import datetime
import hashlib
import json
from urllib.request import build_opener,ProxyHandler

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
manifest=read(HERE/'Activation/manifest.json')
rows=[]
for item in manifest['items']:
    rows.append({'target':item['target'],'applied':digest(Path(item['target']))==item['candidateSha256'],'backupVerified':digest(Path(item['backup']))==item['beforeSha256']})
for item in manifest['newItems']:
    rows.append({'target':item['target'],'applied':digest(Path(item['target']))==item['candidateSha256']})
opener=build_opener(ProxyHandler({}))
with opener.open('http://127.0.0.1:8776/health',timeout=2) as response:health=json.load(response)
with opener.open('http://127.0.0.1:18769/v1/catalog',timeout=2) as response:catalog=json.load(response)
voice_equal=all(digest(path)==digest(HERE/'Current/Voice'/path.name) for path in (HERE/'Final-v3/Voice').glob('*.py'))
render_equal=all(digest(HERE/'Final-v3/Source'/name)==digest(HERE/'Current/Source'/name) for name in ['MrClothCoverageRepair.cs','SubtitleChromaRepair.cs','RenderRepairReview.cs'])
native=ROOT/'NativeMotionAdapt-20261020/Current/Player/MGFR_Data/StreamingAssets/native-actions'
delivered=HERE/'Final-v3/Player/MGFR_Data/StreamingAssets/native-actions'
motion_files=list(native.rglob('*.hpose'))
motion_equal=len(motion_files)==52 and all(digest(path)==digest(delivered/path.relative_to(native)) for path in motion_files)
evidence={
 'liveVoice':HERE/'Voice/live-current-20261020-161038-742942.json',
 'deliveredRecovery':HERE/'Voice/recovery-delivered-20261020-162813-456149.json',
 'deliveredUnityPlayback':HERE/'unity-voice-20261020-162615-675399/result.json',
 'deliveredScale':HERE/'scale-20261020-162410-222186/result.json',
 'materialRender':HERE/'render-20261020-160733-567074/Results/result.json',
 'subtitle':HERE/'SubtitleCandidate/PixelProbe-v2/result.json',
}
checks={name:read(path)['pass'] for name,path in evidence.items()}
passed=all(row['applied'] and row.get('backupVerified',True) for row in rows) and all(checks.values()) and voice_equal and render_equal and motion_equal and health.get('status')=='ok' and health.get('avatarRevision')=='structured-history-natural-clauses-v4' and sum(a.get('callable',True) for a in catalog.get('actions',[]))==19
result={'passWithinAcceptedLimits':passed,'entryFiles':rows,'checks':checks,'nativeMotionFiles':len(motion_files),'nativeMotionUnchanged':motion_equal,'deliveredVoiceMatchesTestedWorker':voice_equal,'deliveredMaterialSourcesMatchTestedPackage':render_equal,'voiceRevision':health.get('avatarRevision'),'player':str(HERE/'Final-v3/Player/MGFR.exe'),'moduleSha256':digest(HERE/'Final-v3/Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'),'evidence':{name:str(path) for name,path in evidence.items()},'acceptedMaterialChoice':'Preserve sheer cloth using discrete coverage; some chroma-stream edges accepted by user','headsetAndActualCodecVerified':False,'clothVideoZeroGreenVerified':False,'activeDefaultEntry':str(ROOT/'启动MGFR.cmd')}
output=HERE/('delivery-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
print(json.dumps({'passWithinAcceptedLimits':passed,'appliedFiles':len(rows),'nativeMotionFiles':len(motion_files),'voiceRevision':health.get('avatarRevision'),'checks':checks,'receipt':str(output)},ensure_ascii=False,indent=2))
raise SystemExit(0 if passed else 1)
