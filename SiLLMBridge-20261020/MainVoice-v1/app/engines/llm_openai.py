"""Persistent streaming connection, stable prompt prefix and per-request cache metrics."""
from __future__ import annotations
import asyncio
import contextvars
import json
import os
import time
from typing import Any,AsyncIterator
import httpx
from ..config import LlmConfig
from ..speech_style import SPOKEN_STYLE
from .base import EngineUnavailable

def _content_deltas(obj:dict[str,Any])->list[str]:
    out=[]
    for choice in obj.get('choices') or ():
        if not isinstance(choice,dict):continue
        delta=choice.get('delta') or choice.get('message') or {}
        if not isinstance(delta,dict):continue
        text=delta.get('content') or delta.get('text')
        if isinstance(text,str) and text:out.append(text)
    return out

class OpenAiCompatLlm:
    name='openai'
    def __init__(self,cfg:LlmConfig)->None:
        self.cfg=cfg;self.system_prompt=(cfg.load_system_prompt()+'\n\n'+SPOKEN_STYLE).strip();self._client=None
        self._request_metrics=contextvars.ContextVar('deepseek_request_metrics',default=None)
    @property
    def metrics(self):return dict(self._request_metrics.get() or {})
    def endpoint(self):return self.cfg.base_url.rstrip('/')+'/chat/completions'
    def build_messages(self,messages):
        return [{'role':'system','content':self.system_prompt},*messages] if self.system_prompt else list(messages)
    def _get_client(self):
        if self._client is None:
            self._client=httpx.AsyncClient(timeout=httpx.Timeout(self.cfg.request_timeout_s,connect=10),trust_env=False,proxy=os.environ.get('MGFR_LLM_PROXY') or None,limits=httpx.Limits(max_connections=8,max_keepalive_connections=4,keepalive_expiry=120))
        return self._client
    async def aclose(self):
        if self._client is not None:await self._client.aclose()
    async def stream(self,messages:list[dict[str,str]],cancel:asyncio.Event)->AsyncIterator[str]:
        key=self.cfg.resolve_api_key()
        if not key:raise EngineUnavailable('LLM credential is not configured')
        started=time.perf_counter();metrics={'firstTokenMs':None,'promptCacheHitTokens':None,'promptCacheMissTokens':None,'promptTokens':None,'completionTokens':None,'newConnection':False}
        self._request_metrics.set(metrics)
        async def trace(event,info):
            if event=='connection.connect_tcp.started':metrics['newConnection']=True
        payload={'model':self.cfg.model,'messages':self.build_messages(messages),'stream':True,'stream_options':{'include_usage':True},'thinking':{'type':'disabled'},'max_tokens':self.cfg.max_tokens,'temperature':self.cfg.temperature}
        payload['response_format']={'type':'json_object'}
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','Accept':'text/event-stream'}
        async with self._get_client().stream('POST',self.endpoint(),json=payload,headers=headers,extensions={'trace':trace}) as response:
            metrics['httpVersion']=response.http_version
            if response.status_code!=200:raise EngineUnavailable(f'DeepSeek returned HTTP {response.status_code}; check model, account and credential')
            async for line in response.aiter_lines():
                if cancel.is_set():return
                if not line.startswith('data:'):continue
                data=line[5:].strip()
                if data=='[DONE]':continue
                try:obj=json.loads(data)
                except json.JSONDecodeError:continue
                if not isinstance(obj,dict):continue
                usage=obj.get('usage')
                if isinstance(usage,dict):
                    for field,source in [('promptCacheHitTokens','prompt_cache_hit_tokens'),('promptCacheMissTokens','prompt_cache_miss_tokens'),('promptTokens','prompt_tokens'),('completionTokens','completion_tokens')]:
                        if source in usage:metrics[field]=usage[source]
                for text in _content_deltas(obj):
                    if metrics['firstTokenMs'] is None:metrics['firstTokenMs']=round((time.perf_counter()-started)*1000,2)
                    yield text
        metrics['totalMs']=round((time.perf_counter()-started)*1000,2)
