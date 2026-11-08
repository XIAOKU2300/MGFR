from pathlib import Path
import hashlib,json,socket
from PIL import Image

root=Path('H:/MGFR');delivery=root/'CodexDelivery-20261018';source=root/'unity-client';project=delivery/'Project'
files=sorted((source/'Assets/MGFR/Scripts/Experience').glob('*.cs'))+[source/'Assets/StreamingAssets/motion/idle.bin']
checks={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256((project/p.relative_to(source)).read_bytes()).hexdigest() for p in files}
assert all(checks.values())
preserved=[]
receipt=json.loads((root/'VRFIX-APPLIED-20261018.json').read_text(encoding='utf-8-sig'))
for item in receipt['files']:
    p=Path(item['path']);good=hashlib.sha256(p.read_bytes()).hexdigest()==item['afterSha256']
    preserved.append(dict(path=str(p),matches_authorized_fix=good));assert good
p=source/'Assets/MGFR/Scripts/Character/SiCharacterLoader.cs'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='55cb0bf284fa0929e452bedc697347a9409758667574d88c45c2c130e7ac913a'
frames=[]
for p in sorted((delivery/'Visual02').glob('pose-*.png')):
    im=Image.open(p).convert('RGB');im.thumbnail((620,620));frames.append(im)
frames[0].save(delivery/'Idle-Skirt-Preview.gif',save_all=True,append_images=frames[1:],duration=180,loop=0)
ports={}
for port in (8765,9880):
    with socket.socket() as s:
        s.settimeout(.4);ports[str(port)]=s.connect_ex(('127.0.0.1',port))==0
report=dict(executable=str(project/'Build/Windows/MGFR.exe'),source_matches_build=checks,preserved_vr_fixes=preserved,
    transparent_skirt_fix_preserved=True,services_listening=ports,
    runtime_checks=(delivery/'Check01/result.txt').read_text(),final_visual_checks=(delivery/'Visual02/visual-result.txt').read_text(),
    headset_test='Not performed: actual controller and binocular headset acceptance require the user.',
    controller_scope='Tracked controller poses + joystick offset + grip/trigger proxy hands. Grab/throw test ball and push skirt. No arm IK or bare-hand tracking.',
    idle_scope='84 baked bones with VMD Bezier interpolation, twist/inherit rotation and leg/toe retarget; live mouth/blink and attention own face.',
    skirt_scope='192 existing skirt joints, 16 columns, spring/inertia/length constraints, leg capsules and hand contact. Lightweight approximation, not full PMX rigid-body physics.')
with (delivery/'delivery-report.json').open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
text='''# 新版体验交付

双击 H:\\MGFR\\启动MGFR新版.cmd，或运行：
H:\\MGFR\\CodexDelivery-20261018\\Project\\Build\\Windows\\MGFR.exe

已完成：
- 用户 Idle2 待机自动循环，约 4.33 秒；保留原动作节奏，末尾做短过渡。模型静止骨架在运行时校正，脚部按本模型腿长定位。原 PMX/VMD 和导出模型文件未改。
- 裙摆轻量物理：192 个现有裙骨，轻微惯性、回弹、约束、腿部与代理手接触。不是完整 MMD 物理；动作文件属于另一套模型的裙/发轨道不硬套。
- 双控制器作为虚拟手代理：实际 6DoF 位姿，摇杆额外平移，扳机或抓握抓起蓝球，放开抛出；靠近裙摆会推动它。不是裸手跟踪，也没有把角色手臂套到用户身上。
- 同时接入此前独立验证的头颈与双眼注意力；看向头显的位置。保留实际播放驱动口型和已有眨眼，不是读取用户眼球视线。

操作：
- VR：先保持 ALVR/SteamVR 连接，再运行新版。手柄靠近蓝球，按扳机/抓握拿起，移动后松开抛出。摇杆可微调代理手位置，累计偏移限 35 cm。
- F3 重置蓝球。
- 无头显时 F2 开启桌面代理手，WASD 移动左手、Q/E 升降；左下角勾选 Left grip，再点 Ball to left 可快速试拿球。
- 角色位置和原来的文字对话操作沿用原版本。旧 run-player.ps1 仍指向旧包，请用本次新入口。

检查：
- 构建成功，0 编译错误，1 条原有 XR 废弃接口警告。
- 首轮 12 项短检查通过：待机、固定锚点、双眼校准、抓取/跟随/释放、裙摆接触/恢复、所有骨骼有效。
- 最终新包实际模型渲染通过：24 帧预览，脚踝最大定位误差约 0.37 mm；裙摆最大偏移约 4.49 cm，求解峰值约 1.39 ms（桌面本次观测）。
- 本次未戴头显；真实控制器输入、双眼观看和头显帧率需在设备上体验确认。桌面代理注入测试不冒充硬件验收。
- 五份已有 VR/透明层修复散列保持一致。主项目新增模块与构建副本源码一致；已有源码没有额外覆盖，未提交/推送。

Claude 的进度：停在读取 VMD 和 PMX 机制阶段，只补了 pmx_reader.py 的 IK/轴数据；尚未做出待机播放器/新包。本次接续完成上面的三项。

证据：delivery-report.json、Check01/result.txt、Visual02/visual-result.txt、Visual02/pose-*.png、Idle-Skirt-Preview.gif。
'''
with (delivery/'交付说明.md').open('x',encoding='utf8') as f:f.write(text)
print(json.dumps(dict(source_files=len(files),all_match=True,ports=ports,report=str(delivery/'交付说明.md')),ensure_ascii=False))
