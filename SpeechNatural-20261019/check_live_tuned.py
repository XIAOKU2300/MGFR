"""Own synthetic prompts only, through the candidate's actual LLM/TTS path."""
from pathlib import Path
import asyncio,json,sys,time,wave
import websockets

LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService8'))
from app.protocol import decode_audio_frame,AudioKind

PROMPTS=[
    '今天事情有点多，我有些累，想先休息一会儿。',
    '现在是12:30，水温26.5摄氏度，进度20%。用自然的一句话帮我确认一下这些信息。',
]

async def main():
    folder=LAB/'LiveTuned';folder.mkdir()
    rows=[]
    for index,prompt in enumerate(PROMPTS,1):
        started=time.perf_counter();first=None;pcm=bytearray();rate=None;channels=None;text='';spoken=[];seq=0;metrics=[]
        async with websockets.connect('ws://127.0.0.1:8773/ws',open_timeout=5,max_size=2**22) as ws:
            async def send(value):await ws.send(json.dumps({'v':1,**value},ensure_ascii=False))
            await send({'type':'hello','client':'synthetic-speech-adaptation-check'})
            await send({'type':'session.start'})
            while True:
                msg=json.loads(await asyncio.wait_for(ws.recv(),15))
                if msg['type']=='error':raise RuntimeError('Candidate handshake failed: '+str(msg.get('code')))
                if msg['type']=='state' and msg.get('state')=='listening':break
            await send({'type':'text.input','text':prompt})
            while True:
                item=await asyncio.wait_for(ws.recv(),120)
                if isinstance(item,bytes):
                    frame=decode_audio_frame(item)
                    assert frame.kind is AudioKind.TTS and frame.seq==seq
                    seq+=1;rate=frame.sample_rate;channels=frame.channels;pcm.extend(frame.payload)
                    if first is None:first=time.perf_counter()-started
                    continue
                msg=json.loads(item)
                if msg['type']=='error':raise RuntimeError('Candidate round failed: '+str(msg.get('code')))
                if msg['type']=='llm.delta':text+=msg['text']
                if msg['type']=='tts.start':spoken.append(msg['text'])
                if msg['type']=='latency':metrics.append({k:v for k,v in msg.items() if k not in ('v','round')})
                if msg['type']=='state' and msg.get('state')=='listening':break
            await send({'type':'session.end'})
        assert text.strip() and pcm and rate==32000 and channels==1
        assert all(not any(marker in item for marker in ('**','……','“','”')) for item in spoken)
        path=folder/(str(index).zfill(2)+'-voice.wav')
        with path.open('xb') as stream:
            with wave.open(stream,'wb') as audio:
                audio.setnchannels(channels);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(pcm)
        row={'prompt':prompt,'reply':text,'spokenPhrases':spoken,'file':str(path),'rate':rate,'audioFrames':seq,
             'audioSeconds':len(pcm)/(rate*channels*2),'firstAudioMs':round(first*1000,1),'metrics':metrics}
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in ('prompt','metrics')},ensure_ascii=False),flush=True)
    with (LAB/'live-tuned-check.json').open('x',encoding='utf-8') as output:
        json.dump({'passed':True,'microphoneUsed':False,'externalLlmSyntheticPromptsOnly':True,'examples':rows},output,ensure_ascii=False,indent=2)

if __name__=='__main__':asyncio.run(main())
