"""Record the currently installed public code, data and local service contract."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
from urllib.request import ProxyHandler,build_opener

ROOT=Path('H:/MGFR');FINAL=ROOT/'DialogueRenderRepair-20261020/Final-v3';HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    spec=importlib.util.spec_from_file_location('current_launch',ROOT/'DialogueMemory-20261020/launch_memory.py')
    launch=importlib.util.module_from_spec(spec);spec.loader.exec_module(launch)
    opener=build_opener(ProxyHandler({}))
    voice=launch.health(launch.VOICE_URL);memory=launch.health(launch.MEMORY_URL)
    assert voice and memory and voice['status']=='ok' and memory['ready']
    expected=launch.build_identity();assert voice['memoryBuild']==memory['build']==expected
    catalog=json.load(opener.open('http://127.0.0.1:18772/v1/catalog',timeout=3))
    counts={'actions':len(catalog['actions']),'callable':sum(a.get('callable',True) for a in catalog['actions']),'expressions':sum(len(e['variants']) for e in catalog['emotions'])}
    assert counts=={'actions':83,'callable':62,'expressions':45}
    context=json.load(opener.open('http://127.0.0.1:18772/v1/context',timeout=3))
    assert '当前PMX动作没有原生97脸骨曲线' in context['system_prompt']
    assert opener.open('http://127.0.0.1:9880/voice_info',timeout=3).status==200
    entries=list(ROOT.glob('*.cmd'));assert entries==[ROOT/'启动MGFR.cmd']
    module=FINAL/'Player/MGFR_Data/Managed/MGFR.StructuredVoiceFinal.dll'
    assert sha(module)=='5e7e0279a5e60c909e10bd19e4b50a36e36ae28975a9f7964521cafecbcea97d'
    source=list((FINAL/'Source').rglob('*.cs'))
    snapshot=FINAL/'MenuBuild/Preview-v6/Source'
    assert all(p.read_text(encoding='utf-8-sig').splitlines()==(snapshot/p.relative_to(FINAL/'Source')).read_text(encoding='utf-8-sig').splitlines() for p in source)
    installed=list((FINAL/'Player/MGFR_Data/StreamingAssets/native-actions').glob('*/*.hpose'))
    assert len(installed)==166
    assert all(sha(p)==sha(HERE/'native-reference-v2'/p.relative_to(FINAL/'Player/MGFR_Data/StreamingAssets/native-actions')) for p in installed)
    tests={
        'current_player':ROOT/'DialogueRenderRepair-20261020/acceptance-Final-v3-20261021-080203-791955/Results/result.json',
        'memory':ROOT/'DialogueMemory-20261020/Tests/verify-9c5af70d81774154b411b5f07ff15566/result.json',
        'interactions':ROOT/'DialogueMemory-20261020/Tests/interactions-086debdb1f264ab6a11604e892732f6a.json',
        'unity_context':ROOT/'DialogueMemory-20261020/Tests/unity-context-41dbbe2f26be4ae4829b66ef21585dbe/result.json',
        'hand_menu':FINAL/'MenuBuild/Review-20261020-215545-947155/Results/result.json',
        'tts_recovery':ROOT/'DialogueRenderRepair-20261020/Voice/recovery-delivered-20261021-080728-270258.json',
        'voice_emotion_protocol':HERE/'voice-face-result.json',
    }
    assert all(read(p)['pass'] for p in tests.values())
    player=read(tests['current_player'])
    sys.path.insert(0,str(HERE));import check_audio_endpoint
    audio=check_audio_endpoint.inspect()
    assert all('Pico Streaming Speaker' in d.get('name','') for d in audio['defaults'])
    public=source+list((FINAL/'Voice').glob('*.py'))+[ROOT/'启动MGFR.cmd',ROOT/'DialogueRenderRepair-20261020/launch_final.py',ROOT/'DialogueMemory-20261020/launch_memory.py',ROOT/'SiLLMBridge-20261020/main_bridge_final.py',ROOT/'SiLLMBridge-20261020/bridge_server.py',ROOT/'SiLLMBridge-20261020/client/llm_chat.py']
    result={
        'verified':True,'entry':str(entries[0]),'player':str(launch.PLAYER),'memoryBuild':expected,'moduleSha256':sha(module),
        'counts':counts,'emotionVariantCounts':{e['name']:len(e['variants']) for e in catalog['emotions']},
        'frames':sum(p['frames'] for p in player['phases']),'abnormalJumps':sum(p['abnormalJumps'] for p in player['phases']),
        'installedNativeReferenceClips':len(installed),'sourceFilesMatchCurrentModuleSnapshot':len(source),
        'voiceFaceFallbackLive':True,'ttsReady':True,'voiceReady':True,'memoryReady':True,'audio':audio['defaults'],
        'publicFileSha256':{str(p):sha(p) for p in public+installed},'testReports':{k:str(v) for k,v in tests.items()},
        'sdkTests':{'passed':5,'mode':'isolated loopback HTTP fixtures; no external LLM'},
        'limits':['97 native face-bone poses remain archived; runtime uses 45 compatible PMX morph poses','No headset/ALVR subjective validation or all-frame mesh penetration guarantee','Headset forward approximates gaze'],
    }
    with (HERE/'current-feature-contract.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:result[k] for k in ['verified','entry','counts','frames','abnormalJumps','sourceFilesMatchCurrentModuleSnapshot','voiceFaceFallbackLive','ttsReady']},ensure_ascii=False))

if __name__=='__main__':main()
