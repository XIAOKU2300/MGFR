from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
workspace=root.parent
release=workspace/'DialogueRenderRepair-20261020'
active=release/'Final-v3'
candidate=root/'Candidate-v2'
out=root/'Activation';out.mkdir()
staged=out/'Staged';staged.mkdir()
def sha(data):return hashlib.sha256(data).hexdigest()
plan=[]
def add(target,data):
    target=target.resolve()
    if not target.is_relative_to(workspace):raise ValueError('Target outside workspace')
    staged_path=staged/target.relative_to(workspace)
    staged_path.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(data,str):data=data.encode('utf-8')
    with staged_path.open('xb') as stream:stream.write(data)
    plan.append({'target':str(target),'staged':str(staged_path),'oldSha256':sha(target.read_bytes()) if target.is_file() else None,'newSha256':sha(data)})
for name in ('mgfr-mr-coverage','gesture-touch-panel-v1'):
    add(active/'Player/MGFR_Data/StreamingAssets'/name,(candidate/'Player/MGFR_Data/StreamingAssets'/name).read_bytes())
add(active/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll',(candidate/'Build/MGFR.StructuredVoiceFinal.dll').read_bytes())
for name in ('NativeAvatarActions-main.cs','XrSessionRecovery.cs','StereoMaterialGpuReview.cs'):
    add(active/'Source'/name,(candidate/'Source'/name).read_bytes())
launcher=(release/'launch_final.py').read_text(encoding='utf-8')
before='    subprocess.Popen(command, cwd=PLAYER.parent)'
assert launcher.count(before)==1
launcher=launcher.replace(before,"    subprocess.Popen([str(PYTHON), '-B', '-X', 'utf8', str(HERE / 'monitor_player.py'), '--log', str(log), '--', *command], cwd=PLAYER.parent, creationflags=subprocess.CREATE_NO_WINDOW)")
add(release/'launch_final.py',launcher)
for name in ('monitor_player.py','verify_stereo_current.py'):
    add(release/name,(root/name).read_bytes())
add(workspace/'测试入口/08-双眼与稳定性.cmd','@echo off\r\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -B -X utf8 "H:\\MGFR\\DialogueRenderRepair-20261020\\verify_stereo_current.py"\r\nif errorlevel 1 pause\r\n')
document=(workspace/'测试入口/说明.md').read_text(encoding='utf-8-sig')
row='| 08-双眼与稳定性.cmd | 当前包32组GPU双眼像素对比；100秒动作、换装、缩放；3次XR退出请求拦截 |\n'
assert '08-双眼与稳定性.cmd' not in document
document=document.replace('\n\n这些测试不录制话筒', '\n'+row+'\n这些测试不录制话筒',1)
add(workspace/'测试入口/说明.md',document)
with (out/'plan.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,ensure_ascii=False,indent=2)
print('EXISTING_TARGET_COUNT',sum(row['oldSha256'] is not None for row in plan))
print('NEW_TARGET_COUNT',sum(row['oldSha256'] is None for row in plan))
for row in plan:print(('OVERWRITE ' if row['oldSha256'] else 'CREATE ')+row['target'])
