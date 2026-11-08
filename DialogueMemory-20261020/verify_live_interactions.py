"""Real LLM/TTS with queued synthetic observations; no mic/device playback."""
from pathlib import Path
import asyncio
import json
import time
import uuid
import httpx
import websockets

HERE=Path(__file__).resolve().parent

async def receive_turn(ws, previous=None):
    result={'pcmBytes':0,'textChars':0,'errors':[],'asrMessages':0,'round':None}
    async with asyncio.timeout(60):
        while True:
            value=await ws.recv()
            if isinstance(value,bytes):result['pcmBytes']+=max(0,len(value)-24);continue
            row=json.loads(value);kind=row.get('type')
            if kind=='llm.delta':result['textChars']+=len(row.get('text',''))
            if kind=='asr.final':result['asrMessages']+=1
            if kind=='error':result['errors'].append(row.get('code'))
            current=row.get('round')
            if current is not None and current!=previous:result['round']=current
            if kind=='state' and row.get('state')=='listening' and result['round'] is not None and current==result['round']:return result

async def main():
    async with httpx.AsyncClient(timeout=3,trust_env=False) as api, websockets.connect('ws://127.0.0.1:8779/ws',max_size=8*1024*1024) as ws:
        await ws.send(json.dumps({'v':1,'type':'hello','clientVersion':'memory-queue-acceptance','audio':{'micSampleRate':16000,'micChannels':1},'capabilities':['text.input']}))
        while json.loads(await ws.recv()).get('type')!='hello.ack':pass
        await ws.send(json.dumps({'v':1,'type':'session.start'}))
        while json.loads(await ws.recv()).get('state')!='listening':pass
        await ws.send(json.dumps({'v':1,'type':'text.input','text':'你好，请说一句简短的问候。'},ensure_ascii=False))
        first=await receive_turn(ws)
        client='live-review-'+uuid.uuid4().hex
        acks=[]
        for index,event in enumerate([
            {'kind':'garment','phase':'removed','part':'shoe_left'},
            {'kind':'touch','phase':'start','region':'left_arm','hand':'right'},
            {'kind':'garment','phase':'equipped','part':'shoe_left'},
        ],1):
            event['event_id']=client+'-'+str(index)
            payload={'client_id':client,'sequence':index,'snapshot':{'skin':'swimsuit','gaze_region':'left_thigh','left_touch':'unknown','right_touch':'left_arm','garment_ids':['shoe_left'],'garment_equipped':[index==3]},'events':[event]}
            response=await api.post('http://127.0.0.1:8779/mgfr-interaction',json=payload)
            response.raise_for_status();acks.append(response.json())
        waited=False
        try:
            await asyncio.wait_for(ws.recv(),timeout=.4)
        except TimeoutError:waited=True
        assert waited and all(x.get('accepted') and x.get('speaking') for x in acks), 'Playback queue did not hold observations'
        await ws.send(json.dumps({'v':1,'type':'playback.finished','round':first['round'],'reason':'completed'}))
        second=await receive_turn(ws,first['round'])
        await ws.send(json.dumps({'v':1,'type':'playback.finished','round':second['round'],'reason':'completed'}))
        await ws.send(json.dumps({'v':1,'type':'session.end'}))
    checks={'real_typed_round':first['pcmBytes']>0 and first['textChars']>0 and not first['errors'],
            'held_until_playback_finished':waited,'three_events_queued_in_order':acks[-1].get('queuedEvents')==3,
            'real_autonomous_audio_reply':second['pcmBytes']>0 and second['textChars']>0 and not second['errors'],
            'no_fake_user_speech':second['asrMessages']==0}
    result={'pass':all(checks.values()),'checks':checks,'first':first,'interactionReply':second,
            'mode':'Real configured LLM and original TTS, synthetic ordered observation packets and playback notifications; no microphone, no device playback'}
    out=HERE/'Tests'/('live-interactions-'+uuid.uuid4().hex+'.json')
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':result['pass'],'result':str(out),'checks':checks},ensure_ascii=False))
    if not result['pass']:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
