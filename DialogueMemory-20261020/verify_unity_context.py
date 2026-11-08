"""Actual current-player observation collection against a synthetic voice backend."""
from pathlib import Path
import asyncio
import json
import os
import socket
import subprocess
import sys
import uuid

HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE/'src_v3'),str(HERE.parent/'SpeechNatural-20261019/VoiceService10')]


async def main():
    import uvicorn
    from app.main import create_app
    from app.config import Config
    from interaction_context import install
    parser=__import__('argparse').ArgumentParser();parser.add_argument('--player',type=Path,required=True);args=parser.parse_args()
    run=HERE/'Tests'/('unity-context-'+uuid.uuid4().hex);run.mkdir()
    config=Config();app=create_app(config);install(app)
    packets=[]
    # Capture the incoming wire data while retaining actual validation/scheduling.
    for route in app.routes:
        if getattr(route,'path','')=='/mgfr-interaction':
            original=route.endpoint
            async def capture(value):
                packets.append(value.model_dump())
                return await original(value)
            route.endpoint=capture;route.dependant.call=capture
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='critical',access_log=False))
    serving=asyncio.create_task(server.serve(sockets=[listener]))
    while not server.started:await asyncio.sleep(.025)
    command=[str(args.player),'-batchmode','-force-d3d11','-screen-width','640','-screen-height','480','-mgfr-noxr','-mgfr-voice-review',
             '-mgfr-structured-voice','-mgfr-dialogue-context','-mgfr-context-review','-mgfr-context-review-out',str(run/'unity.json'),
             '-mgfr-service-url',f'ws://127.0.0.1:{port}/ws','-mgfr-skins','-mgfr-skin','swimsuit',
             '-mgfr-zmd','-mgfr-mr-clean-edge','-mgfr-wardrobe','-mgfr-shoes','-mgfr-avatar-data',str(HERE.parent/'SiLLMBridge-20261020/MainData'),'-logFile',str(run/'player.log')]
    child_env=os.environ.copy()
    # Force this desktop-only fixture to avoid the user's SteamVR runtime.
    # XR_RUNTIME_JSON is the Khronos per-process loader override; selecting a
    # nonexistent test manifest makes XR unavailable without registry changes.
    child_env['XR_RUNTIME_JSON']=str(run/'xr-runtime-disabled.json')
    child=subprocess.Popen(command,cwd=args.player.parent,env=child_env,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline=asyncio.get_running_loop().time()+45
        while child.poll() is None and asyncio.get_running_loop().time()<deadline:await asyncio.sleep(.1)
        if child.poll() is None:child.terminate();raise RuntimeError('Owned Unity review timed out')
    finally:
        server.should_exit=True;await serving
    result=json.loads((run/'unity.json').read_text(encoding='utf-8')) if (run/'unity.json').exists() else {'pass':False,'exitCode':child.returncode}
    events=[event for packet in packets for event in packet['events']]
    observed={(event['kind'],event['phase']) for event in events}
    result['wireEventsVerified']=all(pair in observed for pair in [('gaze','start'),('touch','start'),('garment','removed'),('garment','equipped')])
    result['observedPairs']=sorted([list(pair) for pair in observed])
    with (run/'packets.json').open('x',encoding='utf-8') as out:json.dump(packets,out,ensure_ascii=False,indent=2)
    result['pass']=result['pass'] and result['wireEventsVerified']
    result['packetCount']=len(packets)
    with (run/'result.json').open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':result['pass'],'result':str(run/'result.json'),'regions':result.get('regions'),'packets':len(packets)}))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':asyncio.run(main())
