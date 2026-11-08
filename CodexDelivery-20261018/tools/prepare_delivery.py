from pathlib import Path
import shutil, json, hashlib
root=Path('H:/MGFR');source=root/'unity-client';delivery=root/'CodexDelivery-20261018'
lab=Path('H:/MGFR-Codex-Lab')
mapping={
    lab/'AttentionLab/Release-v2/Core/AttentionDynamics.cs':source/'Assets/MGFR/Scripts/Experience/AttentionDynamics.cs',
    lab/'AttentionLab/Release-v2/Unity/FaceAttentionController.cs':source/'Assets/MGFR/Scripts/Experience/FaceAttentionController.cs',
    delivery/'Motion/idle.bin':source/'Assets/StreamingAssets/motion/idle.bin',
}
for src,dst in mapping.items():
    dst.parent.mkdir(parents=True,exist_ok=True)
    with src.open('rb') as r,dst.open('xb') as w:shutil.copyfileobj(r,w)
project=delivery/'Project'
project.mkdir(exist_ok=False)
for directory in ('Assets','Packages','ProjectSettings'):
    shutil.copytree(source/directory,project/directory)
manifest={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('Assets/MGFR/Scripts/Experience/*.cs')}
with (delivery/'source-hashes.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2)
print('Delivery project:',project)
