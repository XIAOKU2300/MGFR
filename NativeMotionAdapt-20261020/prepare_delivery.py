from pathlib import Path
import json
import hashlib
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='') as f:f.write(text)

def copy_new(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(source.read_bytes())

def main():
    launcher=(PROJECT/'MotionRepair-20261020/launch_main.py').read_text(encoding='utf-8').replace("'release-v1/Player/MGFR.exe'","'Current/Player/MGFR.exe'")
    write(ROOT/'launch_project.py',launcher)
    motion=(ROOT/'run_native_review.py').read_text(encoding='utf-8').replace("default='native-v1'","default='Current'")
    write(ROOT/'test_motion.py',motion)
    catalog=motion.replace("'-mgfr-native-review'","'-mgfr-native-catalog'").replace('timeout=150','timeout=240').replace("'acceptance-'","'catalog-'")
    write(ROOT/'test_catalog.py',catalog)
    voice=(PROJECT/'MotionRepair-20261020/run_network.py').read_text(encoding='utf-8').replace("'release-v1/Player/MGFR.exe'","'Current/Player/MGFR.exe'")
    write(ROOT/'test_voice_pipeline.py',voice)
    write(ROOT/'启动主项目.cmd','@echo off\r\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -B -X utf8 "H:\\MGFR\\NativeMotionAdapt-20261020\\launch_project.py"\r\nif errorlevel 1 pause\r\n')
    tests=ROOT/'测试入口'
    for name,script in [('01-动作连续性.cmd','test_motion.py'),('02-全部可用动作.cmd','test_catalog.py'),('03-语音与LLM动作联调.cmd','test_voice_pipeline.py')]:
        write(tests/name,'@echo off\r\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -B -X utf8 "H:\\MGFR\\NativeMotionAdapt-20261020\\'+script+'"\r\npause\r\n')
    write(tests/'04-原生动作展示.cmd','@echo off\r\npushd "H:\\MGFR\\EndfieldNativeMotions-20261019\\Playable-v2"\r\nstart "" "SiNativePreview.exe"\r\npopd\r\n')
    write(tests/'说明.md','''# 测试入口

这些入口只用于测试与原生对照；日常启动请使用根目录 `H:\\MGFR\\启动MGFR.cmd`。

| 入口 | 内容 |
|---|---|
| 01-动作连续性.cmd | 原生待机循环、对话、LLM动作队列、收尾、打断、换肤、布料碰撞 |
| 02-全部可用动作.cmd | 完整播放19个语音可用动作，按原动作速度基准检查新增突跳 |
| 03-语音与LLM动作联调.cmd | 原JSON适配器、本地模拟LLM/TTS、真实WebSocket/PCM播放、情绪动作同步 |
| 04-原生动作展示.cmd | 打开用户指定的Playable-v2，对照原骨架动作 |

前三项不使用麦克风、头显或远程付费模型。语音测试使用临时本地端口并退出自己创建的进程，不改现有语音服务。每次在 `H:\\MGFR\\NativeMotionAdapt-20261020` 创建新的时间戳报告目录。

特殊待机二原片段约3.8秒处本来就有快速转腕，测试保留它；比较的是适配是否产生额外突变，不把原动作整体压慢。
''')
    navigation='''# MGFR 项目入口

日常只使用根目录 **启动MGFR.cmd**。它加载已验证的终末地原生动作版，保留原语音配置、音色、换肤、ZMD渲染、衣服/鞋子、手部触碰和捏拉。F4静音，F5换肤，F7物理，F11渲染风格沿用原控制。

| 类别 | 位置 | 作用 |
|---|---|---|
| 日常主入口 | `H:\\MGFR\\启动MGFR.cmd` | 唯一推荐的日常启动器 |
| 当前程序 | `H:\\MGFR\\NativeMotionAdapt-20261020\\Current\\Player` | 当前原生动作程序；不要直接双击exe绕过启动参数 |
| 当前动作模块源码 | `H:\\MGFR\\NativeMotionAdapt-20261020\\Current\\Source` | 当前运行DLL对应的源码，以此为准 |
| 当前构建工具 | `H:\\MGFR\\NativeMotionAdapt-20261020\\build_release.py` | 从当前模块源码编译到新目录，不覆盖旧包 |
| 完整Unity底座工程 | `H:\\MGFR\\HandCoexist-20261019\\Project` | 当前包沿用的角色、换肤、交互和物理底座；当前动作由上面的独立模块替换 |
| 测试入口 | `H:\\MGFR\\测试入口` | 连续性、完整动作目录、语音联调、原生对照 |
| 标准Unity动画资产 | `H:\\MGFR\\NativeMotionAdapt-20261020\\UnityAssets-v1\\Assets\\NativeClips` | 两套服装各26段.anim，58根身体/手指/辅助骨骼 |
| 原生动作参考 | `H:\\MGFR\\EndfieldNativeMotions-20261019\\Playable-v2` | 原模型和原骨架展示，作为对照 |
| 动作与表情公共数据 | `H:\\MGFR\\SiLLMBridge-20261020\\MainData` | 保留供当前程序读取，不能当旧文件清理 |
| 语音服务 | `H:\\MGFR\\SpeechNatural-20261019\\VoiceRepair` 与 `VoiceService10` | 现有ASR、LLM、TTS启动链，配置和凭据仍由原程序管理 |
| 早期工程/实验 | `unity-client`、其他日期Player/Project目录、`MotionRepair-20261020` | 历史源码或对照候选，不作为当前日常入口 |

根目录“情绪动作版/情绪动作正式版”、日期目录里的旧“正式版”会启动历史程序，作为旧版对照保留。不要按文件名里的“正式版”选择日常程序。目录没有做批量移动或删除，原件和回退材料都还在。

当前完整说明和验证报告见 `H:\\MGFR\\NativeMotionAdapt-20261020\\README.md`。根目录旧README记录的是早期里程碑，当前入口以本文为准。
'''
    activation=ROOT/'Activation';activation.mkdir(exist_ok=False)
    write(activation/'项目入口说明.md.proposed',navigation)
    copy_new(ROOT/'启动主项目.cmd',activation/'启动MGFR.cmd.proposed')
    targets=[('launcher',PROJECT/'启动MGFR.cmd',activation/'启动MGFR.cmd.proposed'),('navigation',PROJECT/'项目入口说明.md',activation/'项目入口说明.md.proposed')]
    for file in sorted(tests.iterdir()):targets.append(('tests',PROJECT/'测试入口'/file.name,file))
    items=[]
    for group,target,candidate in targets:
        if not target.is_file():raise RuntimeError('Expected existing target is missing: '+str(target))
        backup=activation/'Backups'/target.relative_to(PROJECT)
        copy_new(target,backup)
        items.append({'group':group,'target':str(target),'candidate':str(candidate),'backup':str(backup),'beforeSha256':hashlib.sha256(target.read_bytes()).hexdigest(),'candidateSha256':hashlib.sha256(candidate.read_bytes()).hexdigest()})
    write(activation/'manifest.json',json.dumps({'status':'prepared; awaiting explicit overwrite approval','items':items},ensure_ascii=False,indent=2))
    print('ACTIVATION_PREPARED targets='+str(len(items))+' existing files; three bounded target groups')

if __name__=='__main__':main()
