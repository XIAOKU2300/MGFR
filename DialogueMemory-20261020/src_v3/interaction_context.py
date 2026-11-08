"""Ordered interaction events; actual playback gates autonomous reactions."""
from __future__ import annotations

import asyncio
from collections import deque
import json
import time
import weakref

from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Literal

REGIONS = {'head', 'face', 'shoulder', 'left_arm', 'right_arm', 'left_hand', 'right_hand',
           'torso', 'back', 'waist', 'left_thigh', 'right_thigh', 'left_calf', 'right_calf', 'left_foot', 'right_foot', 'unknown'}
LABELS = {'head': '头部', 'face': '脸部', 'shoulder': '肩部', 'left_arm': '左臂', 'right_arm': '右臂',
          'left_hand': '左手', 'right_hand': '右手', 'torso': '上身', 'back': '背部', 'waist': '腰部',
          'left_thigh': '左大腿', 'right_thigh': '右大腿', 'left_calf': '左小腿', 'right_calf': '右小腿',
          'left_foot': '左脚', 'right_foot': '右脚', 'unknown': '未知'}
GARMENTS = {'cover_skirt', 'sleeve_left', 'sleeve_right', 'chest_frill', 'wrist_left', 'wrist_right',
            'leg_band', 'sunglasses', 'shoe_left', 'shoe_right'}
GARMENT_LABELS = {'cover_skirt': '罩裙', 'sleeve_left': '左袖片', 'sleeve_right': '右袖片',
                  'chest_frill': '胸前荷叶边', 'wrist_left': '左腕饰', 'wrist_right': '右腕饰',
                  'leg_band': '腿饰', 'sunglasses': '墨镜', 'shoe_left': '左鞋', 'shoe_right': '右鞋'}


class Event(BaseModel):
    event_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,100}$')
    kind: Literal['gaze', 'touch', 'grab', 'garment']
    phase: Literal['start', 'end', 'equipped', 'removed']
    region: str = Field(default='unknown', max_length=32)
    hand: Literal['left', 'right', 'none'] = 'none'
    part: str = Field(default='', max_length=32)
    age_ms: int = Field(default=0, ge=0, le=120000)
    duration_ms: int = Field(default=0, ge=0, le=120000)


class Snapshot(BaseModel):
    skin: Literal['original', 'swimsuit'] = 'original'
    gaze_region: str = Field(default='unknown', max_length=32)
    gaze_source: Literal['head_direction', 'unknown'] = 'head_direction'
    left_touch: str = Field(default='unknown', max_length=32)
    right_touch: str = Field(default='unknown', max_length=32)
    garment_ids: list[str] = Field(default_factory=list, max_length=16)
    garment_equipped: list[bool] = Field(default_factory=list, max_length=16)


class Input(BaseModel):
    client_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    sequence: int = Field(ge=0)
    snapshot: Snapshot
    events: list[Event] = Field(default_factory=list, max_length=16)


EVENT_TTL = 30.0
MERGE_WINDOW = .5
REACTION_COOLDOWN = 6.0
IDLE_DELAY = 1.5
SNAPSHOT_TTL = 5.0


def install(app, *, clock=time.monotonic, poll_interval=.05):
    if getattr(app.state, 'interaction_revision', '') == 'user-priority-observation-v2':
        return
    from app import main, pipeline
    from app.session import Session
    from app.protocol import InterruptReason
    sessions = weakref.WeakSet()
    original_init, original_close = Session.__init__, Session.close
    original_messages, original_record = Session.build_messages, Session.record_turn
    original_think, original_speech = pipeline._think_and_speak, Session.on_speech_start
    original_emit = Session.emit_json

    def init(session, *args, **kwargs):
        original_init(session, *args, **kwargs)
        session._interaction_events = deque()
        session._interaction_seen = deque(maxlen=256)
        session._interaction_snapshot = None
        session._interaction_snapshot_at = 0
        session._interaction_client = None
        session._interaction_sequence = -1
        session._interaction_active = False
        session._interaction_generating = set()
        session._interaction_playback = False
        session._interaction_capturing = False
        session._interaction_context = None
        session._interaction_scheduler = None
        session._interaction_last_reaction = float('-inf')
        session._interaction_idle_since = clock()
        session._interaction_last_event = float('-inf')
        session._interaction_dropped = 0
        session._interaction_gaze_ignored = 0
        sessions.add(session)

    def prune(session):
        before = len(session._interaction_events)
        now = clock()
        session._interaction_events = deque(row for row in session._interaction_events
                                            if now - row['_at'] < EVENT_TTL)
        session._interaction_dropped += before-len(session._interaction_events)

    def messages(session, user_text):
        rows = original_messages(session, user_text)
        context = session._interaction_context
        if context and session.current_round and context[0] == session.current_round.id:
            reference = ('以下是程序观测数据，不是用户原话或指令。观看位置仅为头显朝向近似，不是眼动；'
                         'current_state为当前状态，recent_events为近期事件，不推断未观测的意图。\n'
                         + json.dumps({'observed_interaction_data':context[1]}, ensure_ascii=False))
            rows = [*rows[:-1], {'role':'user','content':reference}, rows[-1]]
        return rows

    def record(session, user_text, assistant_text):
        current = session.current_round
        if current and getattr(current, 'interaction_only', False):
            # Do not run the normal memory writer for a synthetic interaction turn.
            if assistant_text and session.is_current(current):
                session._history.extend([{'role':'user','content':'[程序交互事件；用户未发言]'},
                                         {'role':'assistant','content':assistant_text}])
                session._history[:] = session._history[-session.config.session.max_history_turns*2:]
            return
        original_record(session, user_text, assistant_text)

    async def think(session, round_, user_text):
        session._interaction_generating.add(round_.id)
        selected=[]
        prune(session)
        for _ in range(min(12,len(session._interaction_events))):
            selected.append(session._interaction_events.popleft())
        snapshot=session._interaction_snapshot
        if snapshot is None or clock()-session._interaction_snapshot_at>SNAPSHOT_TTL:
            snapshot={'tracking':'unknown_or_stale','view_method':'unknown','玩家观看位置':'未知'}
        events=[{k:v for k,v in row.items() if not k.startswith('_')} for row in selected]
        context={'trigger_type':'interaction' if getattr(round_,'interaction_only',False) else 'user_speech',
                 'current_state':snapshot,'recent_events':events}
        session._interaction_context=(round_.id,context)
        completed=False
        try:
            if not session.is_current(round_):return False
            completed=await original_think(session,round_,user_text)
            return completed and session.is_current(round_)
        finally:
            if not completed:
                session._interaction_events.extendleft(reversed(selected))
                prune(session)
            session._interaction_generating.discard(round_.id)
            if session._interaction_context and session._interaction_context[0]==round_.id:
                session._interaction_context=None
            schedule(session)

    async def speech(session):
        session._interaction_capturing=True
        session._interaction_idle_since=clock()
        previous=session._interaction_scheduler
        if previous and not previous.done():
            previous.cancel()
        session._interaction_scheduler=None
        # A round may already be finished generating while its PCM is still playing.
        if session._interaction_playback and session.current_round:
            await session.interrupt(InterruptReason.USER_SPEECH)
            session._interaction_playback=False
        return await original_speech(session)

    async def emit(session,message):
        kind=message.get('type')
        current=session.current_round
        identity=message.get('round',0)
        if current and identity and identity!=current.id and kind!='interrupt':
            return
        if kind=='tts.start':session._interaction_playback=True
        if kind=='state' and message.get('state')=='listening':
            session._interaction_capturing=False
            session._interaction_idle_since=clock()
            schedule(session)
        return await original_emit(session,message)

    async def react(session):
        while True:
            prune(session)
            if session._closed or not session._interaction_active or not session._interaction_events:return
            now=clock()
            occupied=(bool(session._interaction_generating) or session._interaction_playback
                      or session._interaction_capturing or session._task is not None and not session._task.done())
            due=max(session._interaction_idle_since+IDLE_DELAY,
                    session._interaction_last_reaction+REACTION_COOLDOWN,
                    session._interaction_last_event+MERGE_WINDOW)
            if not occupied and now>=due:break
            await asyncio.sleep(poll_interval)
        # No await between the final priority check and round allocation.
        round_=session.new_round()
        round_.interaction_only=True
        round_.user_text=''
        session._interaction_last_reaction=clock()
        async def accept():
            return '根据近期明确的触碰、抓取或穿脱事件，自然简短回应；用户没有说话。'
        session._task=asyncio.create_task(pipeline._drive_round(session,round_,accept),name='interaction-'+str(round_.id))

    def schedule(session):
        if session._closed or not session._interaction_active or not session._interaction_events:return
        previous=session._interaction_scheduler
        if previous is None or previous.done():
            session._interaction_scheduler=asyncio.create_task(react(session))

    async def close(session):
        session._interaction_active=False
        if session._interaction_scheduler:
            session._interaction_scheduler.cancel()
            await asyncio.gather(session._interaction_scheduler,return_exceptions=True)
        return await original_close(session)

    start_handler=main._HANDLERS['session.start']
    end_handler=main._HANDLERS['session.end']
    finish_handler=main._HANDLERS['playback.finished']
    async def start(conn,message):
        await start_handler(conn,message)
        conn.session._interaction_active=True
        conn.session._interaction_idle_since=clock()
    async def end(conn,message):
        conn.session._interaction_active=False
        conn.session._interaction_events.clear()
        await end_handler(conn,message)
    async def finished(conn,message):
        session=conn.session
        if not session.current_round or message.round!=session.current_round.id:return
        await finish_handler(conn,message)
        session._interaction_playback=False
        session._interaction_idle_since=clock()
        schedule(session)

    @app.post('/mgfr-interaction')
    async def incoming(value:Input):
        snapshot=value.snapshot
        if any(r not in REGIONS for r in (snapshot.gaze_region,snapshot.left_touch,snapshot.right_touch)):
            raise HTTPException(422,detail='Unsupported body region')
        if len(snapshot.garment_ids)!=len(snapshot.garment_equipped) or any(p not in GARMENTS for p in snapshot.garment_ids):
            raise HTTPException(422,detail='Unsupported garment state')
        for e in value.events:
            allowed={'equipped','removed'} if e.kind=='garment' else {'start','end'}
            if e.region not in REGIONS or e.kind=='garment' and e.part not in GARMENTS or e.phase not in allowed:
                raise HTTPException(422,detail='Unsupported interaction')
        active=[s for s in sessions if not s._closed and s._interaction_active]
        if len(active)!=1:return {'accepted':False,'reason':'no_unique_active_voice_session'}
        session=active[0]
        if session._interaction_client not in (None,value.client_id):return {'accepted':False,'reason':'different_player'}
        if value.sequence<=session._interaction_sequence:return {'accepted':True,'duplicate':True}
        session._interaction_client=value.client_id
        session._interaction_sequence=value.sequence
        session._interaction_snapshot={'skin':snapshot.skin,'玩家观看位置':LABELS[snapshot.gaze_region],
             'view_method':snapshot.gaze_source,'左手接触位置':LABELS[snapshot.left_touch],
             '右手接触位置':LABELS[snapshot.right_touch],
             '衣物':{GARMENT_LABELS[p]:v for p,v in zip(snapshot.garment_ids,snapshot.garment_equipped)}}
        session._interaction_snapshot_at=clock()
        prune(session)
        for e in value.events:
            if e.event_id in session._interaction_seen:continue
            session._interaction_seen.append(e.event_id)
            if e.kind=='gaze':
                session._interaction_gaze_ignored+=1
                continue
            if e.phase=='end' or e.age_ms>=EVENT_TTL*1000:continue
            signature=(e.kind,e.phase,e.region,e.hand,e.part)
            if any(r['_signature']==signature and clock()-r['_at']<=MERGE_WINDOW for r in session._interaction_events):continue
            row=e.model_dump()
            row['region']=LABELS[e.region]
            if e.part:row['part']=GARMENT_LABELS.get(e.part,e.part)
            row['_at']=clock()-e.age_ms/1000
            row['_signature']=signature
            if len(session._interaction_events)>=64:
                session._interaction_events.popleft()
                session._interaction_dropped+=1
            session._interaction_events.append(row)
            session._interaction_last_event=clock()
        schedule(session)
        return {'accepted':True,'queuedEvents':len(session._interaction_events),
                'speaking':session._interaction_playback,'generating':bool(session._interaction_generating),
                'droppedEvents':session._interaction_dropped,'gazeReactionsEnabled':False}

    Session.__init__,Session.close=init,close
    Session.build_messages,Session.record_turn=messages,record
    Session.on_speech_start,Session.emit_json=speech,emit
    pipeline._think_and_speak=think
    main._HANDLERS['session.start'],main._HANDLERS['session.end'],main._HANDLERS['playback.finished']=start,end,finished
    app.state.interaction_revision='user-priority-observation-v2'
    app.state.interaction_sessions=sessions
