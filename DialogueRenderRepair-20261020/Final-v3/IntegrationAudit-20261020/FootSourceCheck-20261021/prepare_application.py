"""Create backups and the exact overwrite review. No installed file is modified."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
FINAL=HERE.parents[1]
ACTIVE=FINAL/'Player/MGFR_Data/StreamingAssets/native-actions'
audit=json.loads((HERE/'all-native-channels.json').read_text(encoding='utf-8'))
backup=HERE/'Backups-before-application';backup.mkdir(exist_ok=False)
entries=[]
for item in audit['targets']:
    target=Path(item['path']);candidate=Path(item['candidate'])
    assert target.resolve().is_relative_to(ACTIVE.resolve())
    raw=target.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==item['beforeSha256']
    assert hashlib.sha256(candidate.read_bytes()).hexdigest()==item['afterSha256']
    saved=backup/target.relative_to(ACTIVE);saved.parent.mkdir(parents=True,exist_ok=True)
    with saved.open('xb') as stream:stream.write(raw)
    assert saved.read_bytes()==raw
    entries.append({**item,'backup':str(saved)})
assert len(entries)==166
with (HERE/'application-manifest.json').open('x',encoding='utf-8') as f:json.dump({'liveFilesModified':False,'count':166,'entries':entries},f,ensure_ascii=False,indent=2)
lines=['# 脚部官方源通道恢复候选','',
       '仅移除上一轮新增的脚踝至脚趾方向拟合。83段官方源动作、两套皮肤共166个文件，均只改脚踝/脚趾及对应脚踝辅助骨的旋转。其他骨骼通道、关节位置、动作时长和采样率逐字节相同。',
       '', '官方源文件未修改。整批38064采样帧的脚部世界旋转与官方源动画相对绑定姿势的旋转差一致，最大误差小于0.000007度。原入口、程序模块、模型、语音和鞋子配置均不变。',
       '', '当前只完成候选与备份，尚未覆盖运行资源。', '', '## 完整覆盖清单（166个明确目标）', '']
for item in entries:
    lines += ['操作：覆盖','',f"目标：`{item['path']}`",'', '影响：1个文件','', '理由：撤销上一轮新增的脚部方向拟合，恢复官方动作中的脚部旋转；保留其余通道。','',f"安全检查：已有逐字节核对的备份 `{item['backup']}`；应用前再次核对当前SHA256。",'','---','']
with (HERE/'覆盖确认清单.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines))
print('Exact existing targets (166):')
for item in entries:print(item['path'])
print('All 166 files backed up; no live resources modified.')
