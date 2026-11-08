"""Real LLM/TTS through the installed candidate WebSocket; receive PCM without playback."""
from pathlib import Path
import asyncio
import json
import struct
import time
import uuid
import websockets

HERE=Path(__file__).resolve().parent


async def main():
    results=[]
    async with websockets.connect('ws://127.0.0.1:8779/ws',max_size=8*1024*1024) as ws:
        await ws.send(json.dumps({'v':1,'type':'hello','clientVersion':'memory-upgrade-acceptance','audio':{'micSampleRate':16000,'micChannels':1},'capabilities':['text.input']}))
        while json.loads(await ws.recv()).get('type')!='hello.ack':pass
        await ws.send(json.dumps({'v':1,'type':'session.start'}))
        while json.loads(await ws.recv()).get('state')!='listening':pass
        for index,text in enumerate(['你好，今天想和你聊两句。','你最擅长什么能力？','刚才我们聊到了什么？'],1):
            started=time.perf_counter();entry={'turn':index,'pcmBytes':0,'firstTextMs':None,'firstPcmMs':None,'metrics':[],'errors':[]};reply='';round_id=None
            await ws.send(json.dumps({'v':1,'type':'text.input','text':text},ensure_ascii=False))
            async with asyncio.timeout(70):
                while True:
                    frame=await ws.recv()
                    if isinstance(frame,bytes):
                        entry['pcmBytes']+=max(0,len(frame)-24)
                        if entry['firstPcmMs'] is None:entry['firstPcmMs']=round((time.perf_counter()-started)*1000,2)
                        continue
                    message=json.loads(frame);kind=message.get('type')
                    if kind=='asr.final':round_id=message.get('round')
                    if kind=='llm.delta':
                        reply+=message.get('text','')
                        if entry['firstTextMs'] is None:entry['firstTextMs']=round((time.perf_counter()-started)*1000,2)
                    if kind=='latency':entry['metrics'].append({k:v for k,v in message.items() if k not in {'v','round','ts'}})
                    if kind=='error':entry['errors'].append(message.get('code'))
                    if kind=='state' and message.get('state')=='listening' and round_id is not None and message.get('round')==round_id:break
            entry['textChars']=len(reply);entry['fallback']='刚才那句没说完整' in reply
            entry['seconds']=round(time.perf_counter()-started,2)
            entry['pass']=bool(reply.strip()) and entry['pcmBytes']>0 and not entry['errors'] and not entry['fallback']
            results.append(entry)
            await ws.send(json.dumps({'v':1,'type':'playback.finished','round':round_id,'reason':'completed'}))
        await ws.send(json.dumps({'v':1,'type':'session.end'}))
    report={'pass':all(x['pass'] for x in results),'mode':'Real configured LLM, original GPT-SoVITS variant 1, WebSocket and PCM; typed input bypasses microphone/ASR; PCM received without device playback','turns':results}
    out=HERE/'Tests'/('real-voice-'+uuid.uuid4().hex+'.json')
    with out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({'pass':report['pass'],'result':str(out),'firstPcmMs':[x['firstPcmMs'] for x in results],'errors':[x['errors'] for x in results]}))
    if not report['pass']:raise SystemExit(1)


if __name__=='__main__':asyncio.run(main())
