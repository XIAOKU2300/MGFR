from pathlib import Path
import ast,hashlib,json
root=Path(__file__).resolve().parent
release=root.parent/'DialogueRenderRepair-20261020'
activation=json.loads((root/'Activation/activation-receipt.json').read_text(encoding='utf-8'))
for row in activation['files']:
    if hashlib.sha256(Path(row['target']).read_bytes()).hexdigest()!=row['newSha256']:raise RuntimeError('Installed file differs from verified candidate')
for name in ('launch_final.py','monitor_player.py','verify_stereo_current.py'):
    ast.parse((release/name).read_text(encoding='utf-8'))
audit=(root/'Bundle-final/variant-audit.txt').read_text(encoding='utf-8').splitlines()
for row in audit:
    variants=row.split('|')[4].split(';')
    assert any('STEREO_INSTANCING_ON' in v for v in variants)
    assert any('STEREO_INSTANCING_ON' not in v for v in variants)
    assert 'MGFR_BUILD_STEREO_VARIANT' not in row
checks={
 'stereoAndStability':root/'Review-stability-20261020-211429-082964/result.json',
 'gpu32':root/'Review-stability-20261020-211429-082964/Stereo/result.json',
 'render':root/'Review-render-20261020-211314-474254/Results/result.json',
 'activeScale':root/'Review-scale-20261020-211806-193063/result.json',
 'activeNative':root/'Review-native-20261020-211936-364102/Results/result.json',
 'activeMenu':root/'Review-menu-monitored-20261020-212140-346632/Results/result.json'
}
results={key:json.loads(path.read_text(encoding='utf-8-sig')).get('pass') is True for key,path in checks.items()}
assert all(results.values())
snapshot=json.loads((root/'Candidate-v2/source-snapshot.json').read_text(encoding='utf-8'))
changed={row['target'] for row in activation['files']}
for name,digest in snapshot.items():
    if name not in changed:assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
receipt={'pass':True,'installedFilesVerified':len(activation['files']),'compiledPassStagesWithMonoAndStereo':len(audit),'checks':results,'mainEntry':str(root.parent/'启动MGFR.cmd'),'testEntry':str(root.parent/'测试入口/08-双眼与稳定性.cmd'),'headsetWornValidation':False,'physicalHeadsetReconnectValidated':False,'backups':str(root/'Activation/backup-receipt.json')}
with (root/'delivery.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,ensure_ascii=False,indent=2)
print(json.dumps(receipt,ensure_ascii=True,indent=2))
