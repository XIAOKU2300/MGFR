"""Synthetic user facts through the original configured real LLM; no TTS/microphone."""
from pathlib import Path
import asyncio
import json
import os
import runpy
import socket
import subprocess
import sys
import time
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path[:0]=[str(HERE/'src_v3'),str(ROOT/'SpeechNatural-20261019/VoiceService10')]


async def main():
    import httpx,uvicorn
    from fastapi import FastAPI
    from launch_memory import environment,MEMORY_URL,VOICE_PORT,MEMORY_PORT,VOICE_URL,MEMORY_PYTHON
    run=HERE/'Tests'/('live-memory-'+uuid.uuid4().hex);run.mkdir()
    os.environ['MGFR_MEMORY_DATA']=str(run/'store')
    env=environment()
    # Original bootstrap is the only code that reads/decrypts the real credential.
    namespace=runpy.run_path(str(ROOT/'SpeechNatural-20261019/VoiceService10/voice_server.py'),run_name='mgfr_live_memory_config')
    configured=namespace['namespace']['app'].state.config
    for port in [VOICE_PORT,MEMORY_PORT]:
        with socket.socket() as check:check.bind(('127.0.0.1',port))
    callback=FastAPI();callback.state.config=configured
    from voice_memory import install
    install(callback,url=MEMORY_URL,token=env['MGFR_MEMORY_TOKEN'])
    server=uvicorn.Server(uvicorn.Config(callback,host='127.0.0.1',port=VOICE_PORT,log_level='critical',access_log=False))
    serving=asyncio.create_task(server.serve())
    while not server.started:await asyncio.sleep(.025)
    for key in ['MGFR_LLM_API_KEY','OPENAI_API_KEY','DEEPSEEK_API_KEY']:env.pop(key,None)
    log=(run/'memory-worker.log').open('xb')
    child=subprocess.Popen([str(MEMORY_PYTHON),'-B','-X','utf8',str(HERE/'launch_memory.py'),'--memory-worker'],cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    result={'pass':False,'mode':'Real original configured LLM via original credential bootstrap; real Mem0 and CPU embedding; synthetic user facts; no TTS or microphone'}
    try:
        async with httpx.AsyncClient(timeout=2,trust_env=False,headers={'X-MGFR-Memory-Key':env['MGFR_MEMORY_TOKEN']}) as client:
            deadline=time.monotonic()+35
            while time.monotonic()<deadline:
                try:
                    health=(await client.get(MEMORY_URL+'/health')).json()
                    if health.get('ready'):break
                except (httpx.HTTPError,ValueError):pass
                if child.poll() is not None:raise RuntimeError('Memory worker exited')
                await asyncio.sleep(.15)
            else:raise RuntimeError('Memory worker not ready')
            rounds=[]
            for index,text,word in [(1,'我平常喝茉莉花茶，喜欢泡得淡一点。','茉莉'),(2,'我现在不喝茉莉花茶了，改喝普洱，请以后以这个偏好为准。','普洱')]:
                started=time.perf_counter()
                response=await client.post(MEMORY_URL+'/turns',json={'event_id':'live-'+str(index),'text':text,'user_id':'synthetic-acceptance','character_id':'si'})
                if not response.json().get('accepted'):raise RuntimeError('Test turn was not queued')
                deadline=time.monotonic()+35
                while time.monotonic()<deadline:
                    health=(await client.get(MEMORY_URL+'/health')).json()
                    if health.get('pendingWrites')==0:break
                    await asyncio.sleep(.2)
                else:raise RuntimeError('Extraction did not finish: '+str(health.get('lastFailureType')))
                response=await client.post(MEMORY_URL+'/context',json={'text':'你记得我现在喜欢什么茶吗？','user_id':'synthetic-acceptance','character_id':'si'})
                found=response.json().get('memories',[])
                success=any(word in row['text'] for row in found)
                rounds.append({'turn':index,'expectedFactRetrieved':success,'writeAndRecallSeconds':round(time.perf_counter()-started,2),'retrievalMs':response.json().get('processingMs')})
            result.update(rounds=rounds,pass_=all(x['expectedFactRetrieved'] for x in rounds))
            result['pass']=result.pop('pass_')
    except Exception as error:
        result['errorType']=type(error).__name__
    finally:
        if child.poll() is None:child.terminate()
        await asyncio.to_thread(child.wait,timeout=8)
        log.close();server.should_exit=True;await serving
    with (run/'result.json').open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':result['pass'],'result':str(run/'result.json'),'rounds':result.get('rounds'),'errorType':result.get('errorType')}))
    if not result['pass']:raise SystemExit(1)


if __name__=='__main__':asyncio.run(main())
