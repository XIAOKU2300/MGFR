"""Apply the reviewed, bounded animation update to the existing daily player."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

ROOT=Path('H:/MGFR')
FINAL=ROOT/'DialogueRenderRepair-20261020/Final-v3'
HERE=Path(__file__).resolve().parent
CANDIDATE=HERE/'native-reference-v2'
ACTIVE=FINAL/'Player/MGFR_Data/StreamingAssets/native-actions'
STAMP=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
BACKUP=HERE/('Applied-'+STAMP)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    module=FINAL/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'
    expected='5e7e0279a5e60c909e10bd19e4b50a36e36ae28975a9f7964521cafecbcea97d'
    assert sha(module)==expected,'Concurrent player change; stop rather than overwrite'
    paths=json.loads((HERE/'overwrite-targets.json').read_text(encoding='utf-8'))['targets']
    pairs=[(Path(p),CANDIDATE/Path(p).relative_to(ACTIVE)) for p in paths]
    assert len(pairs)==166 and all(a.is_file() and b.is_file() for a,b in pairs)
    assert all(a.resolve().is_relative_to(ACTIVE.resolve()) for a,b in pairs)
    docs=[ROOT/'项目入口说明.md',ROOT/'SiLLMBridge-20261020/client/llm_chat.py',ROOT/'SiLLMBridge-20261020/client/README.md']
    legacy=[ROOT/'启动MGFR-情绪动作版.cmd',ROOT/'启动MGFR-情绪动作正式版.cmd']
    assert all(p.is_file() for p in docs+legacy)
    BACKUP.mkdir(exist_ok=False)
    entries=[]
    for active,new in pairs:
        dest=BACKUP/'Backups/native-actions'/active.relative_to(ACTIVE)
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(active.read_bytes())
        entries.append({'path':str(active),'before':sha(active),'after':sha(new),'backup':str(dest)})
    for p in docs+legacy:
        dest=BACKUP/'Backups'/p.relative_to(ROOT)
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(p.read_bytes())
    # Every animation was verified and backed up before the first replacement.
    for active,new in pairs:
        with active.open('wb') as f:f.write(new.read_bytes())
    sdk=docs[1];text=sdk.read_text(encoding='utf-8')
    assert text.count('DEFAULT_SERVICE_URL = "http://127.0.0.1:18766"')==1
    sdk.write_text(text.replace('DEFAULT_SERVICE_URL = "http://127.0.0.1:18766"','DEFAULT_SERVICE_URL = "http://127.0.0.1:18772"'),encoding='utf-8')
    p=docs[2];text=p.read_text(encoding='utf-8').replace('http://127.0.0.1:18766','http://127.0.0.1:18772')
    text=text.replace('保留动作原生面部，不叠加情绪表情','不叠加情绪表情；当前PMX运行包不重放原生97脸骨')
    p.write_text(text,encoding='utf-8')
    p=docs[0];text=p.read_text(encoding='utf-8')
    text=text.replace('两套服装共52份Unity动画','83段动作、两套皮肤共166份当前姿势资源；62段开放给LLM')
    text=text.replace('其他日期包、根目录旧“情绪动作正式版”、','其他日期包、已归档的旧“情绪动作版”入口、')
    text+='\n统一版本核对（2026-10-21）：以本入口实际加载的 Final-v3 主程序和长期记忆服务为准。包含83段动作（62段可调用）、45个情绪表情（8类，每类至少3个）、JSON动作/情绪输出、防重复、多轮对话与TTS、长期记忆、交互排队和当前手势面板。肩臂动作已改为原版参考坐标直接对应，取消这批资源的HumanPose肌肉空间二次转换；保留既有皮肤与绑定、根部轨迹和衣物系统。原生97脸骨预设保留归档，运行表情使用45个PMX兼容形态，不能称作97脸骨原样重放。\n\n唯一日常启动入口仍是 `H:\\MGFR\\启动MGFR.cmd`；根目录两个旧情绪版入口已保留原件并归档为不可执行副本。详细功能和本轮验证见 `H:\\MGFR\\DialogueRenderRepair-20261020\\Final-v3\\CURRENT_FEATURES.md`。\n'
    p.write_text(text,encoding='utf-8')
    archive=BACKUP/'LegacyEntries';archive.mkdir()
    for p in legacy:
        destination=archive/(p.name+'.disabled')
        assert p.resolve().parent==ROOT.resolve() and not destination.exists()
        p.rename(destination)
    assert sha(module)==expected and all(sha(a)==sha(b) for a,b in pairs)
    receipt={'applied':True,'player':str(FINAL/'Player/MGFR.exe'),'entry':str(ROOT/'启动MGFR.cmd'),'moduleUnchanged':sha(module),'animationCount':len(pairs),'entries':entries,'legacyEntriesArchived':str(archive),'backups':str(BACKUP/'Backups')}
    with (BACKUP/'receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
    print(json.dumps({'applied':True,'animations':len(pairs),'receipt':str(BACKUP/'receipt.json')},ensure_ascii=False))

if __name__=='__main__':main()
