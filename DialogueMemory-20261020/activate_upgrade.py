"""Activate exactly five backed-up files; refuse changes to the reviewed base."""
from pathlib import Path
import hashlib
import json
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
ACTIVE=ROOT/'DialogueRenderRepair-20261020/Final-v3'
CANDIDATE=HERE/'Builds/candidate-e007d5606a7840168b175b005a2323b3'
UNITY_REVIEW=HERE/'Tests/unity-context-4c5a94733c3c4a9182dc4debce01df67/result.json'
MENU_REVIEW=ACTIVE/'MenuBuild/Review-20261020-213151-594996/Results/result.json'

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def create(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(data if isinstance(data,bytes) else data.encode('utf-8'))

def main():
    receipt=json.loads((CANDIDATE/'receipt.json').read_text(encoding='utf-8'))
    compiled=CANDIDATE/'MGFR.StructuredVoiceFinal.dll'
    assert sha(compiled)==receipt['sha256']
    for path,digest in receipt['baseHashes'].items():
        if sha(Path(path))!=digest:raise RuntimeError('Current runtime changed after review: '+path)
    for report in (UNITY_REVIEW,MENU_REVIEW):
        if not json.loads(report.read_text(encoding='utf-8-sig'))['pass']:raise RuntimeError('Required review failed')
    acceptance=json.loads((HERE/'acceptance-final.json').read_text(encoding='utf-8'))
    if not acceptance['pass']:raise RuntimeError('Final acceptance incomplete')
    module=ACTIVE/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'
    source=ACTIVE/'Source/NativeAvatarActions-main.cs'
    entry=ROOT/'启动MGFR.cmd'
    description=ROOT/'项目入口说明.md'
    targets=[module,source,ACTIVE/'receipt.json',description,entry]
    entry_text=entry.read_text(encoding='utf-8-sig')
    old=str(ROOT/'DialogueRenderRepair-20261020/launch_final.py')
    if entry_text.count(old)!=1:raise RuntimeError('Root launcher changed; refusing to overwrite')
    entry_text=entry_text.replace(old,str(HERE/'launch_memory.py'))
    doc=description.read_text(encoding='utf-8-sig')
    replacements=[
        ('当前已启用握拳召唤','当前已启用长期记忆、角色资料检索、交互事件排队和握拳召唤'),
        ('`H:\\MGFR\\DialogueRenderRepair-20261020\\launch_final.py` | 当前程序、8776语音与18769动作接口','`H:\\MGFR\\DialogueMemory-20261020\\launch_memory.py` | 当前程序、8779语音、18772动作与18780记忆接口'),
        ('日常当前版使用8776/18769。','日常当前版使用8779/18772/18780，9880仍为原语音模型；8776/18769等旧服务保留。'),
    ]
    for before,after in replacements:
        if doc.count(before)!=1:raise RuntimeError('Entry documentation changed; refusing implicit rewrite')
        doc=doc.replace(before,after)
    doc+='\n对话升级说明：`H:\\MGFR\\DialogueMemory-20261020\\README.md`。用户长期记忆和角色资料分别存储；说话时交互按顺序排队，空闲时回应，用户开口优先。角色进入前静音预热，检索超过120毫秒直接继续对话。注视为头显朝向近似。管理记忆和编辑资料的方法见该说明。当前正在运行的其他程序未被关闭，下次从主入口启动生效。\n'
    updated=json.loads((ACTIVE/'receipt.json').read_text(encoding='utf-8'))
    updated.update(moduleSha256=sha(compiled),memoryUpgrade={'root':str(HERE),'revision':'mem0-role-memory-v1','baseModuleSha256':receipt['baseHashes'][str(module)],'candidate':str(CANDIDATE),'acceptance':str(HERE/'acceptance-final.json')})
    new_sources=[(CANDIDATE/'Source'/name,ACTIVE/'Source'/name) for name in ('MgfrInteractionContext.cs','MgfrContextReview.cs')]
    if any(destination.exists() for _,destination in new_sources):raise RuntimeError('New source already exists')
    # Include all other player assets, source, original voice adapters and private
    # config in a digest-only preservation check. Never copy or print credentials.
    protected=[p for p in (ACTIVE/'Player').rglob('*') if p.is_file() and p!=module]
    protected+=[p for p in (ACTIVE/'Source').rglob('*') if p.is_file() and p!=source]
    protected+=list((ACTIVE/'Voice').glob('*.py'))
    protected+=[ROOT/'DialogueRenderRepair-20261020/launch_final.py',ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice.toml']
    protected_before={str(p):sha(p) for p in protected}
    activation=HERE/'Activations'/('activation-'+uuid.uuid4().hex)
    backups=[]
    for target in targets:
        backup=activation/'Backups'/target.relative_to(ROOT)
        create(backup,target.read_bytes())
        if sha(backup)!=sha(target):raise RuntimeError('Backup verification failed')
        backups.append({'target':str(target),'backup':str(backup),'beforeSha256':sha(target)})
    create(activation/'before.json',json.dumps({'targets':backups,'protected':protected_before},ensure_ascii=False,indent=2))
    print(json.dumps({'operation':'backed-up activation','existingFileCount':len(targets),'targets':[str(p) for p in targets],'backup':str(activation/'Backups')},ensure_ascii=False),flush=True)
    for staged,destination in new_sources:create(destination,staged.read_bytes())
    source.write_bytes((CANDIDATE/'Source/NativeAvatarActions-main.cs').read_bytes())
    module.write_bytes(compiled.read_bytes())
    (ACTIVE/'receipt.json').write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    description.write_text(doc,encoding='utf-8')
    if {str(p):sha(p) for p in protected}!=protected_before:raise RuntimeError('Protected file changed during activation')
    if sha(module)!=receipt['sha256']:raise RuntimeError('Installed module hash mismatch')
    # Entry switches only after the complete module and documentation are ready.
    entry.write_text(entry_text,encoding='utf-8',newline='')
    result={'pass':True,'activation':str(activation),'moduleSha256':sha(module),'backups':backups,
            'rootEntry':str(entry),'player':str(ACTIVE/'Player/MGFR.exe'),'protectedFilesUnchanged':len(protected),
            'newSources':[str(p) for _,p in new_sources]}
    create(activation/'activated.json',json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'pass':True,'activation':str(activation),'protectedFilesUnchanged':len(protected)},ensure_ascii=False))

if __name__=='__main__':main()
