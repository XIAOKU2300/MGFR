from pathlib import Path
import asyncio
import json
import random
import struct
import sys
import unittest
from types import SimpleNamespace

LAB=Path(__file__).resolve().parent
sys.path.insert(0,str(LAB/'VoiceService10'))
from app.text import SentenceAccumulator, normalize_for_speech, split_sentences
from app.config import Config, LlmConfig, TtsConfig
from app.engines.base import AudioChunk
from app.engines.factory import Engines
from app.engines.llm_openai import OpenAiCompatLlm
from app.engines.tts_gptsovits import GptSovitsTts, _ResponseAudioParser
from app.pipeline import run_text_round
from app.session import Session
from app.protocol import InterruptReason


class SpeechTextTests(unittest.TestCase):
    def test_spoken_punctuation(self):
        cases={
            '……我在听，你慢慢说。':'我在听，你慢慢说。',
            '我……想你了。':'我，想你了。',
            '真的？！不许骗我！！！':'真的？不许骗我！',
            '祀：“别急，我会陪着你。”':'别急，我会陪着你。',
            '（轻笑）**先坐一会儿**，别紧张。':'先坐一会儿，别紧张。',
            '*轻笑* 过来吧～':'过来吧。',
            '现在是12:30，长度3.5cm，比例20%。':'现在是12点30分，长度3.5厘米，比例百分之20。',
            '温度26.5°C左右，长度3.5cm长。':'温度26.5摄氏度左右，长度3.5厘米长。',
            '总数1,234.5，变化-2.5%。':'总数1234.5，变化百分之负2.5。',
            '版本v2.0.3，PICO 4可以用。':'版本v2.0.3，PICO 4可以用。',
            '[看看说明](https://example.invalid/doc)，再试一次。':'看看说明，再试一次。',
            '🙂……！！***':'',
            '<think>不应朗读的推理。</think>我在这里。':'我在这里。',
            '3.5……再确认一下。':'3.5，再确认一下。',
        }
        for original,expected in cases.items():
            with self.subTest(original=original):
                self.assertEqual(normalize_for_speech(original),expected)
                self.assertEqual(normalize_for_speech(expected),expected)

    def test_a_short_reply_is_one_semantic_request(self):
        text='先坐一会儿。事情又不会趁你休息的时候跑掉。'
        self.assertEqual(split_sentences(text),[text])

    def test_stream_chunk_boundaries_do_not_break_numbers_or_quotes(self):
        cases=['“别急，我在听。”你慢慢说就好！','现在是12:30，长度3.5cm，比例20%。','……我在听。别着急，慢慢说就好。','**别紧张**，我只是想问：你今天过得怎么样？！']
        for text in cases:
            expected=split_sentences(text)
            for width in range(1,len(text)+1):
                acc=SentenceAccumulator();out=[]
                for i in range(0,len(text),width):out.extend(acc.push(text[i:i+width]))
                out.extend(acc.flush())
                self.assertEqual(out,expected,(text,width,out,expected))

    def test_punctuation_only_tail_is_never_synthesized(self):
        self.assertEqual(split_sentences('你好，今天过得怎么样？！？……'),['你好，今天过得怎么样？'])

    def test_long_text_is_bounded_without_splitting_ascii_words(self):
        out=split_sentences(('今天我们先把事情处理好，再慢慢坐下来聊聊。'*20))
        self.assertTrue(all(len(item)<=96 for item in out))
        acc=SentenceAccumulator(max_chars=16)
        result=acc.push('我们检查abcdefghijklmnopqrstuvwxyz这个版本，确认没有缺字。')+acc.flush()
        self.assertIn('abcdefghijklmnopqrstuvwxyz',''.join(result))

    def test_quality_profile_and_reference_voice_are_preserved(self):
        cfg=TtsConfig(ref_audio='LOCAL_REFERENCE.wav',prompt_text='原参考台词。')
        payload=GptSovitsTts(cfg).payload('“……先坐一会儿，好吗？！”')
        self.assertEqual(payload['text'],'先坐一会儿，\n好吗？')
        self.assertEqual(payload['text_split_method'],'cut0')
        self.assertEqual(payload['streaming_mode'],1)
        self.assertEqual(payload['ref_audio_path'],cfg.ref_audio)
        self.assertEqual(payload['prompt_text'],cfg.prompt_text)
        self.assertEqual(payload['speed_factor'],1)
        self.assertEqual((payload['top_k'],payload['top_p'],payload['temperature'],payload['repetition_penalty']),(15,.85,.65,1.2))

    def test_tts_breaks_only_complete_sentences(self):
        payload=GptSovitsTts(TtsConfig()).payload('先坐一会儿。事情又不会趁你休息的时候跑掉。')
        self.assertEqual(payload['text'],'先坐一会儿。\n事情又不会趁你休息的时候跑掉。')
        self.assertNotIn('\n',GptSovitsTts(TtsConfig()).payload('事情又不会趁你休息的时候跑掉，我们明天再说。')['text'])

    def test_short_lead_in_is_protected_for_the_installed_voice(self):
        payload=GptSovitsTts(TtsConfig()).payload('先坐一会儿吧，事情又不会趁你休息的时候跑掉。')
        self.assertEqual(payload['text'],'先坐一会儿吧，\n事情又不会趁你休息的时候跑掉。')

    def test_stable_spoken_style_is_added_without_changing_user_messages(self):
        engine=OpenAiCompatLlm(LlmConfig(system_prompt_file='nonexistent-test-prompt'))
        messages=[{'role':'user','content':'原始问题？'}]
        prepared=engine.build_messages(messages)
        self.assertIn('完整、顺口的短句',prepared[0]['content'])
        self.assertEqual(prepared[1:],messages)
        self.assertEqual(engine.build_messages(messages),prepared)

    def test_wav_parser_keeps_pcm_and_observed_rate(self):
        pcm=bytes(range(200));fmt=struct.pack('<HHIIHH',1,1,32000,64000,2,16)
        body=b'fmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(pcm))+pcm
        wav=b'RIFF'+struct.pack('<I',len(body)+4)+b'WAVE'+body
        parser=_ResponseAudioParser(24000)
        data=b''.join(parser.feed(wav[i:i+7]) for i in range(0,len(wav),7))
        self.assertEqual(data,pcm);self.assertEqual(parser.sample_rate,32000);self.assertTrue(parser.rate_is_observed)


class PcmPauseTests(unittest.TestCase):
    def test_voiced_samples_are_unchanged_and_excess_quiet_is_bounded(self):
        import numpy as np
        from app.speech_pcm import SpeechPcmSmoother
        rate=32000
        tone=(np.sin(np.arange(rate//5)*2*np.pi*240/rate)*6000).astype('<i2').tobytes()
        quiet=bytes(rate*2)
        original=quiet+tone+quiet+tone+quiet
        smoother=SpeechPcmSmoother(rate,1)
        actual=b''.join(smoother.push(original[i:i+317]) for i in range(0,len(original),317))+smoother.flush()
        self.assertEqual(actual.count(tone),2)
        self.assertLessEqual(len(actual)/(rate*2),.04+.2+.32+.2+.1+.01)
        self.assertGreater(smoother.dropped_bytes,0)

    def test_quiet_only_input_does_not_create_a_spoken_clip(self):
        from app.speech_pcm import SpeechPcmSmoother
        smoother=SpeechPcmSmoother(32000,1)
        self.assertEqual(smoother.push(bytes(64000))+smoother.flush(),b'')


class CompletenessTests(unittest.TestCase):
    def test_omitted_words_and_numbers_are_rejected(self):
        from app.speech_verify import speech_completeness
        for expected,heard in [('先歇着吧。','嗯。'),('现在是十二点半。','水温26.5度。'),('温度26.5摄氏度。','温度25度。')]:
            self.assertLess(speech_completeness(expected,heard),.72)

    def test_asr_numeric_spelling_and_erhua_are_accepted(self):
        from app.speech_verify import speech_completeness
        for expected,heard in [('现在是十二点半。','啊，现在是12点半。'),('先坐一会儿吧。','先坐一会吧。'),('温度26.5摄氏度。','温度26.5度。'),('进度百分之20。','进度20%。'),('进度两成。','进度20%。')]:
            self.assertGreaterEqual(speech_completeness(expected,heard),.72,(expected,heard))


class ClockCompletenessTests(unittest.TestCase):
    def test_written_clock_minutes_match_half_hour_readback(self):
        from app.speech_verify import speech_completeness
        self.assertGreaterEqual(speech_completeness('现在是十二点三十分。','现在是12点半。'),.72)
        self.assertLess(speech_completeness('现在是十二点三十分。','现在是12点20分。'),.72)


class FakeLlm:
    name='local-test-llm'
    def __init__(self,text):self.text=text
    async def stream(self,messages,cancel):
        for char in self.text:
            if cancel.is_set():return
            yield char
            await asyncio.sleep(0)


class CaptureTts:
    name='local-test-tts'
    def __init__(self,slow=False):self.texts=[];self.slow=slow
    def invalidate(self):pass
    async def synthesize(self,text,cancel):
        self.texts.append(text)
        for i in range(40 if self.slow else 2):
            if cancel.is_set():return
            yield AudioChunk(b'\0'*1280,32000,1)
            await asyncio.sleep(.01 if self.slow else 0)


class SpeechPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_subtitles_stay_original_and_speech_gets_normalized(self):
        reply='（轻笑）**先坐一会儿**。这个数值是3.5cm，不是35cm？！'
        tts=CaptureTts();session=Session(engines=Engines(None,None,FakeLlm(reply),tts),config=Config(),out=asyncio.Queue())
        turn=session.new_round()
        await run_text_round(session,turn,'合成测试')
        items=[]
        while not session.out.empty():items.append(session.out.get_nowait())
        controls=[json.loads(item) for item in items if isinstance(item,str)]
        self.assertEqual(''.join(item['text'] for item in controls if item['type']=='llm.delta'),reply)
        self.assertTrue(turn.finished)
        self.assertEqual(turn.assistant_text,reply)
        self.assertEqual(''.join(tts.texts),normalize_for_speech(reply))
        self.assertTrue(any(isinstance(item,bytes) for item in items))
        self.assertEqual(sum(item['type']=='audio.done' for item in controls),1)

    async def test_interruption_still_stops_audio(self):
        tts=CaptureTts(slow=True);session=Session(engines=Engines(None,None,FakeLlm('先坐一会儿。事情又不会趁你休息的时候跑掉。'),tts),config=Config(),out=asyncio.Queue())
        turn=session.new_round();task=asyncio.create_task(run_text_round(session,turn,'测试'))
        for i in range(100):
            if turn.tts_seq:break
            await asyncio.sleep(.01)
        self.assertGreater(turn.tts_seq,0)
        await session.interrupt(InterruptReason.USER_SPEECH);session.drain_outbox()
        await asyncio.wait_for(task,2)
        await asyncio.sleep(.03)
        self.assertTrue(session.out.empty())

    async def test_protected_phrases_use_separate_serial_requests(self):
        class Engine(GptSovitsTts):
            def __init__(self):super().__init__(TtsConfig());self.requests=[]
            async def _stream(self,text,epoch,cancel):
                self.requests.append(text)
                yield AudioChunk(b'\0'*1280,32000,1)
        engine=Engine()
        chunks=[chunk async for chunk in engine.synthesize('先坐一会儿吧，事情又不会趁你休息的时候跑掉。',asyncio.Event())]
        self.assertEqual(engine.requests,['先坐一会儿吧，','事情又不会趁你休息的时候跑掉。'])
        self.assertEqual(len(chunks),2)

    async def test_bad_synthesis_is_retried_before_any_audio_is_emitted(self):
        class Verifier:
            def __init__(self):self.calls=0
            async def transcribe(self,samples,rate):
                self.calls+=1;return '嗯。' if self.calls==1 else '先歇着吧。'
        class Engine(GptSovitsTts):
            async def _stream(self,text,epoch,cancel,options=None):
                yield AudioChunk(b'\1\0'*640,32000,1)
        engine=Engine(TtsConfig());engine.verifier=Verifier()
        chunks=[chunk async for chunk in engine.synthesize('先歇着吧。',asyncio.Event())]
        self.assertEqual(len(chunks),1);self.assertEqual(engine.quality_retries,1);self.assertEqual(engine.verified_phrases,1)

    async def test_real_adapter_reports_empty_or_silent_audio_without_crashing(self):
        import httpx
        from app.engines.base import EngineUnavailable
        for pcm in (b'',bytes(32000)):
            fmt=struct.pack('<HHIIHH',1,1,32000,64000,2,16)
            body=b'fmt '+struct.pack('<I',16)+fmt+b'data'+struct.pack('<I',len(pcm))+pcm
            wav=b'RIFF'+struct.pack('<I',len(body)+4)+b'WAVE'+body
            client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,content=wav)),trust_env=False)
            engine=GptSovitsTts(TtsConfig());engine._client=client
            try:
                with self.assertRaises(EngineUnavailable):
                    async for chunk in engine.synthesize('这是一段本机测试。',asyncio.Event()):pass
            finally:await engine.aclose()

    async def test_punctuation_only_reply_never_calls_tts(self):
        tts=CaptureTts();session=Session(engines=Engines(None,None,FakeLlm('……！！🙂'),tts),config=Config(),out=asyncio.Queue())
        turn=session.new_round();await run_text_round(session,turn,'测试')
        self.assertEqual(tts.texts,[])


if __name__=='__main__':unittest.main(verbosity=2)
