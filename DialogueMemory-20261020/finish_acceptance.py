"""Collect actual acceptance reports and verify live identities without private output."""
from pathlib import Path
import hashlib
import json
import time
from urllib.request import Request
from launch_memory import OPENER, build_identity, health

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def main():
    reports={
        'memory_and_knowledge':HERE/'Tests/verify-5dde0193f7a24f28b3fdcc89cb668fd7/result.json',
        'interaction_scheduler':HERE/'Tests/interactions-070903a29a9c4de594a9ed895a30023c.json',
        'real_llm_extraction':HERE/'Tests/live-memory-7cf40874e5c04f569e667b82d71135cc/result.json',
        'current_unity_observations':HERE/'Tests/unity-context-4c5a94733c3c4a9182dc4debce01df67/result.json',
        'current_hand_panel':ROOT/'DialogueRenderRepair-20261020/Final-v3/MenuBuild/Review-20261020-213151-594996/Results/result.json',
        'rare_name_readback':HERE/'Tests/rare-speech-e624ef2311244940987a68c723852812.json',
        'real_continuous_voice':HERE/'Tests/real-voice-e8ea43105a8d4debb4b410da7e8a5fea.json',
        'real_queued_interaction_voice':HERE/'Tests/live-interactions-bd535707f2eb4e93911aa57fe568dd02.json',
    }
    loaded={name:json.loads(path.read_text(encoding='utf-8-sig')) for name,path in reports.items()}
    if not all(report.get('pass') for report in loaded.values()):raise RuntimeError('Required acceptance failed')
    voice=health('http://127.0.0.1:8779');memory=health('http://127.0.0.1:18780')
    expected=build_identity()
    assert voice['memoryBuild']==memory['build']==expected
    assert voice['status']=='ok' and memory['ready'] and voice['speechWarmup']['ready']
    deadline=time.monotonic()+20
    while memory['pendingWrites'] and time.monotonic()<deadline:
        time.sleep(.2);memory=health('http://127.0.0.1:18780')
    assert memory['pendingWrites']==0 and memory['lastFailureType'] is None
    with OPENER.open('http://127.0.0.1:18772/v1/catalog',timeout=2) as response:catalog=json.load(response)
    callable_actions=sum(item.get('callable',True) for item in catalog.get('actions',[]))
    assert callable_actions==62
    token=(HERE/'Data/local-auth.token').read_text(encoding='ascii').strip()
    request=Request('http://127.0.0.1:18780/memories',headers={'X-MGFR-Memory-Key':token})
    with OPENER.open(request,timeout=2) as response:memories=json.load(response)
    memory_count=len(memories['results'])
    # This new production store has only received neutral acceptance prompts.
    # Synthetic persistent facts were placed in separate test stores.
    assert memory_count==0, 'Review neutral acceptance extraction before activating'
    model=HERE/'Models/bge-small-zh-manual-v1/model_optimized.onnx'
    with model.open('rb') as f:model_sha=hashlib.file_digest(f,'sha256').hexdigest()
    assert model_sha=='1294ea4b6331115a353d81f96b85e8c8d7fdcc284453d5b2fab5b016230aad38'
    result={'pass':True,'build':expected,'activeBase':str(ROOT/'DialogueRenderRepair-20261020/Final-v3'),
            'reports':{name:{'pass':True,'path':str(path)} for name,path in reports.items()},
            'memoryContextSamplesMs':loaded['memory_and_knowledge']['memoryContextMs'],
            'realFirstPcmMs':[turn['firstPcmMs'] for turn in loaded['real_continuous_voice']['turns']],
            'realMemoryOverheadMs':[next(item['processingMs'] for item in turn['metrics'] if item.get('stage')=='memory') for turn in loaded['real_continuous_voice']['turns']],
            'foregroundMemoryBudgetMs':120,'callableActions':callable_actions,'productionAcceptanceFacts':memory_count,
            'liveMemory':memory,'liveVoice':voice,'embeddingModelSha256':model_sha,
            'limits':['Headset gaze is a head-direction proxy, not eye tracking','Synthetic hand inputs and typed text; no microphone/device playback in acceptance','Cold speech preparation occurs before player launch; this run reused an already running original TTS model','Prior failed diagnostics are retained under Tests'],
            'previousDiagnostics':{'coldStart':'Tests/real-voice-76cdfc068bcc43ccbb8bd83e19664521.json','rareNameFailure':'Tests/real-voice-1bbb8c4a472f421f9a228857a238ab7b.json'}}
    result['reviewedPlayer']=str(HERE/'Builds/candidate-e007d5606a7840168b175b005a2323b3/Player/MGFR.exe')
    with (HERE/'acceptance-final.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':True,'report':str(HERE/'acceptance-final.json'),'realFirstPcmMs':result['realFirstPcmMs'],'memoryOverheadMs':result['realMemoryOverheadMs'],'productionFacts':memory_count},ensure_ascii=False))

if __name__=='__main__':main()
