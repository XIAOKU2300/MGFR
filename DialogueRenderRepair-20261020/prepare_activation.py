"""List and back up only the six reviewed existing entry files; no overwrites."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
OUT=HERE/'Activation'
OUT.mkdir(exist_ok=False)
def create(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:stream.write(text.encode('utf-8') if isinstance(text,str) else text)
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def command(script):return '@echo off\r\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -B -X utf8 "'+str(HERE/script)+'"\r\nif errorlevel 1 pause\r\n'
navigation='''# MGFR 当前项目入口

日常入口统一使用 `H:\\MGFR\\启动MGFR.cmd`。当前为多轮对话、字幕绿底、透明服装和等比缩放修复版，保留原生动作、音色、表情、换肤和穿脱。

| 类别 | 完整位置 | 用途 |
|---|---|---|
| 主入口 | `H:\\MGFR\\启动MGFR.cmd` | 日常启动，自动检查本次语音服务 |
| 当前启动代码 | `H:\\MGFR\\DialogueRenderRepair-20261020\\launch_final.py` | 当前程序、8776语音与18769动作接口 |
| 当前程序 | `H:\\MGFR\\DialogueRenderRepair-20261020\\Final-v3\\Player` | 当前原生动作与渲染/缩放修复包，勿绕过启动参数直接开exe |
| 当前源码 | `H:\\MGFR\\DialogueRenderRepair-20261020\\Final-v3\\Source` 与 `Voice` | 当前运行模块和语音修复源码 |
| 本次说明 | `H:\\MGFR\\DialogueRenderRepair-20261020\\README-current.md` | 修复依据、验证、薄纱透视取舍和限制 |
| 测试入口 | `H:\\MGFR\\测试入口` | 动作、离线对话、渲染与衣物比例测试 |
| 原生动作参考 | `H:\\MGFR\\EndfieldNativeMotions-20261019\\Playable-v2` | 原骨架展示对照 |
| 动作/表情公共数据 | `H:\\MGFR\\SiLLMBridge-20261020\\MainData` | 当前仍在读取，不能按旧目录清理 |
| 完整Unity底座 | `H:\\MGFR\\HandCoexist-20261019\\Project` | 沿用角色、换肤、衣物和交互底座；当前独立模块以上述Source为准 |
| 原语音资源 | `H:\\MGFR\\SpeechNatural-20261019` | 继续复用原配置、识别模型和TTS；不复制凭据 |
| 原生动作资产 | `H:\\MGFR\\NativeMotionAdapt-20261020\\UnityAssets-v1\\Assets\\NativeClips` | 两套服装共52份Unity动画 |

F4静音、F5换肤、F7物理、F11风格切换沿用原控制。角色缩放时，穿着和脱下的衣物随角色等比缩放；布料仍可运动。

薄纱按用户选择保留透视，绿幕下使用细网点覆盖；串流可能保留少量绿边。字幕使用中性实底。尚未进行头显/ALVR实际编码视觉验收。

其他日期包、根目录旧“情绪动作正式版”、早期`unity-client`和本次目录的Release/Current/Final候选均为历史或验证材料。不要根据“正式版”“Current”“Final”字样选入口。原服务8773/18766保留，日常当前版使用8776/18769。没有批量删除或移动原目录。
'''
test_readme='''# 测试入口

日常启动使用 `H:\\MGFR\\启动MGFR.cmd`，下面只用于测试。

| 入口 | 内容 |
|---|---|
| 01-动作连续性.cmd | 当前包待机、对话、LLM队列、收尾、打断、换肤、布料 |
| 02-全部可用动作.cmd | 完整播放19个语音动作，按原动作速度检测新增突跳 |
| 03-语音与LLM动作联调.cmd | 离线模拟多轮空输出、重试、失败、超时、打断；实际Unity播放PCM与情绪/身体动作 |
| 04-原生动作展示.cmd | Playable-v2原骨架对照 |
| 05-透明材质检查.cmd | 当前包两套服装、两种风格、绿幕与普通相机渲染对比 |
| 06-衣物缩放检查.cmd | 0.2、0.5、1、2、4倍和缩回；检查模拟布面与脱下鞋子比例 |

这些测试不录制话筒，不请求远程付费LLM。每次创建新的时间戳报告，不覆盖旧结果。真实LLM/TTS四轮联调的既有报告在本次修复README所指的Voice目录，不是上述离线模拟测试。

渲染测试不会证明头显/ALVR编码零绿边。薄纱按用户选择保留细网点透视，可能有少量串流绿边。特殊待机二的原片段快速转腕继续保留。
'''
plans=[
 ('launcher',ROOT/'启动MGFR.cmd',command(Path('launch_final.py')),'启用已验证的本次修复程序'),
 ('navigation',ROOT/'项目入口说明.md',navigation,'明确当前主包、源码、语音和历史目录'),
 ('test_motion',ROOT/'测试入口/01-动作连续性.cmd',command(Path('test_motion.py')),'测试当前交付包'),
 ('test_catalog',ROOT/'测试入口/02-全部可用动作.cmd',command(Path('test_catalog.py')),'测试当前交付包'),
 ('test_dialogue',ROOT/'测试入口/03-语音与LLM动作联调.cmd',command(Path('test_dialogue.py')),'加入多轮恢复与当前Unity播放验证'),
 ('test_readme',ROOT/'测试入口/说明.md',test_readme,'补全渲染和等比缩放测试分类'),
]
items=[]
for group,target,text,reason in plans:
    if not target.is_file():raise RuntimeError('Expected exact existing entry missing')
    relative=target.relative_to(ROOT)
    backup=OUT/'Backups'/relative
    proposed=OUT/'Proposed'/relative
    create(backup,target.read_bytes());create(proposed,text)
    if digest(backup)!=digest(target):raise RuntimeError('Backup mismatch')
    items.append({'group':group,'target':str(target),'candidate':str(proposed),'backup':str(backup),'beforeSha256':digest(target),'candidateSha256':digest(proposed),'reason':reason})
new_items=[]
for name,script in [('05-透明材质检查.cmd','test_material_final_player.py'),('06-衣物缩放检查.cmd','test_scale_final.py')]:
    target=ROOT/'测试入口'/name
    if target.exists():raise RuntimeError('New entry already exists; requires separate approval')
    candidate=OUT/'Proposed/测试入口'/name
    create(candidate,command(Path(script)))
    new_items.append({'target':str(target),'candidate':str(candidate),'candidateSha256':digest(candidate)})
create(OUT/'manifest.json',json.dumps({'status':'prepared; awaiting explicit overwrite approval','items':items,'newItems':new_items},ensure_ascii=False,indent=2))
review='# 本次启用覆盖清单\n\n共6个已存在文件，均已逐一备份并校验SHA256；尚未覆盖。\n\n'
for item in items:
    review+='操作：覆盖\n\n目标：`'+item['target']+'`\n\n影响：1个文件\n\n理由：'+item['reason']+'\n\n安全检查：已备份并核对哈希；备份 `'+item['backup']+'`\n\n---\n\n'
review+='另新增2个不存在的测试入口：\n\n'+''.join('- `'+item['target']+'`\n' for item in new_items)
create(OUT/'覆盖确认清单.md',review)
print(json.dumps({'existingCount':len(items),'allBackupsVerified':True,'targets':[item['target'] for item in items],'newCount':len(new_items),'review':str(OUT/'覆盖确认清单.md')},ensure_ascii=False,indent=2))
