"""Exercise real session cancellation and the interaction scheduler with synthetic audio."""
from pathlib import Path
import asyncio
import json
import sys
import types
import uuid

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'src_v3'),str(HERE.parent/'SpeechNatural-20261019/VoiceService10')]


async def main():
    import httpx
    from app import main as voice_main, pipeline
    from app.config import Config
    from app.session import Session
    from app.engines.factory import build_all
    from app.protocol import ControlMessage
    calls=[]
    async def synthetic_reply(session, round_, text):
        calls.append({'round':round_.id,'interactionOnly':getattr(round_,'interaction_only',False),
                      'text':text,'messages':session.build_messages(text)})
        await asyncio.sleep(.01)
        await session.emit_json({'v':1,'type':'tts.start','round':round_.id})
        round_.assistant_text='我知道了。'
        await session.emit_json({'v':1,'type':'audio.done','round':round_.id})
        return True
    pipeline._think_and_speak=synthetic_reply
    from interaction_context import install
    cfg=Config();application=voice_main.create_app(cfg);install(application)
    session=Session(engines=build_all(cfg),config=cfg,out=asyncio.Queue())
    session._interaction_active=True
    initial=session.new_round();initial.finished=True;session._interaction_playback=True
    connection=types.SimpleNamespace(session=session)
    client=httpx.AsyncClient(transport=httpx.ASGITransport(app=application),base_url='http://voice.test')
    sequence=0
    def payload(events, equipped=True):
        nonlocal sequence
        sequence+=1
        return {'client_id':'player-one','sequence':sequence,'snapshot':{
            'skin':'swimsuit','gaze_region':'left_thigh','left_touch':'left_arm',
            'garment_ids':['shoe_left'],'garment_equipped':[equipped]},'events':events}
    def event(i,kind,phase,**extra):
        return {'event_id':'test-'+str(i),'kind':kind,'phase':phase,**extra}
    one=payload([event(1,'garment','removed',part='shoe_left')],False)
    assert (await client.post('/mgfr-interaction',json=one)).json()['queuedEvents']==1
    two=payload([event(2,'touch','start',region='left_arm',hand='right')],False)
    await client.post('/mgfr-interaction',json=two)
    three=payload([event(3,'garment','equipped',part='shoe_left')],True)
    await client.post('/mgfr-interaction',json=three)
    await asyncio.sleep(.35)
    assert not calls, 'Interaction interrupted ongoing playback'
    await voice_main._HANDLERS['playback.finished'](connection,ControlMessage('playback.finished',initial.id,{'reason':'completed'}))
    await asyncio.sleep(.3)
    assert len(calls)==1 and calls[0]['interactionOnly']
    context=json.loads(calls[0]['messages'][-2]['content'].split('\n',1)[1])['observed_interaction_data']
    assert [row['phase'] for row in context['recent_events']]==['removed','start','equipped']
    assert context['current_state']['衣物']['左鞋'] is True
    assert all(json.loads(item).get('type')!='asr.final' for item in list(session.out._queue) if isinstance(item,str))
    checks={'waits_for_actual_playback_finished':True,'preserves_order_and_latest_clothing_state':True,
            'one_batched_reaction_without_fake_asr':True}
    count=len(session._interaction_events)
    assert (await client.post('/mgfr-interaction',json=three)).json()['duplicate']
    assert len(session._interaction_events)==count
    checks['duplicate_packets_are_idempotent']=True
    await client.post('/mgfr-interaction',json=payload([event(4,'gaze','start',region='left_thigh',duration_ms=900)]))
    await asyncio.sleep(.3)
    assert len(calls)==1
    await session.begin_text_turn('我想先说一件事。')
    await session._task
    assert len(calls)==2 and not calls[-1]['interactionOnly']
    assert '我想先说一件事' in calls[-1]['text']
    assert 'left_thigh' not in calls[-1]['messages'][-2]['content']  # regions are translated for the model
    assert '左大腿' in calls[-1]['messages'][-2]['content']
    checks['user_speech_has_priority_and_receives_pending_events']=True
    current=session.current_round
    await voice_main._HANDLERS['playback.finished'](connection,ControlMessage('playback.finished',initial.id,{}))
    assert session._interaction_playback
    checks['stale_playback_notification_ignored']=True
    invalid=payload([event(5,'touch','start',region='invented_region')])
    assert (await client.post('/mgfr-interaction',json=invalid)).status_code==422
    other=payload([]);other['client_id']='other-player'
    assert not (await client.post('/mgfr-interaction',json=other)).json()['accepted']
    checks['fixed_regions_and_player_isolation']=True
    await session.close();await client.aclose()
    out=HERE/'Tests'/('interactions-'+uuid.uuid4().hex+'.json')
    result={'pass':all(checks.values()),'checks':checks,'mode':'Real session/ASGI scheduler and cancellation; synthetic PCM playback notifications and LLM'}
    with out.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':result['pass'],'checks':len(checks),'result':str(out)}))


if __name__=='__main__':
    asyncio.run(main())
