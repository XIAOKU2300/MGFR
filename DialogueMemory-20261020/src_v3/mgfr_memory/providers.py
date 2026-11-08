"""Local CPU embeddings and a credential-free callback to the original voice app."""
from __future__ import annotations

import os
import json
import re
import threading
from collections import OrderedDict
from pathlib import Path

import httpx

MODEL = 'BAAI/bge-small-zh-v1.5'
_lock = threading.RLock()
_model = None
_cache = OrderedDict()


def embedding_model():
    global _model
    with _lock:
        if _model is None:
            from fastembed import TextEmbedding
            _model = TextEmbedding(
                model_name=MODEL, threads=2,
                cache_dir=os.environ['MGFR_MEMORY_MODELS'],
                providers=['CPUExecutionProvider'],
                specific_model_path=os.environ.get('MGFR_MEMORY_MODEL_PATH'),
                local_files_only=os.environ.get('MGFR_MEMORY_DOWNLOAD') != '1',
            )
        return _model


class CpuEmbedding:
    def __init__(self, config=None):
        self.config = config

    def embed(self, text, memory_action=None):
        if not isinstance(text, str):
            raise ValueError('Embedding input must be text')
        mode = 'query' if memory_action == 'search' else 'passage'
        key = (mode, text[:1800])
        with _lock:
            if key in _cache:
                _cache.move_to_end(key)
                return list(_cache[key])
            model = embedding_model()
            rows = model.query_embed(key[1]) if mode == 'query' else model.passage_embed([key[1]])
            vector = next(iter(rows)).tolist()
            _cache[key] = vector
            while len(_cache) > 256:
                _cache.popitem(last=False)
            return list(vector)

    def embed_batch(self, texts, memory_action=None):
        return [self.embed(text, memory_action) for text in texts]


class OriginalVoiceLlm:
    """Only the original voice process resolves its original LLM credential."""
    def __init__(self, config=None):
        self.config = config
        self.client = httpx.Client(timeout=14, trust_env=False)

    def generate_response(self, messages, response_format=None, tools=None, tool_choice='auto', **kwargs):
        if tools:
            raise ValueError('Memory extraction does not expose tools')
        try:
            result = self.client.post(
                os.environ['MGFR_MEMORY_EXTRACT_URL'],
                headers={'X-MGFR-Memory-Key': os.environ['MGFR_MEMORY_TOKEN']},
                json={'messages': messages, 'response_format': response_format},
            )
            if result.status_code != 200:
                raise RuntimeError('Memory extraction deferred')
            content = result.json()['content']
            if not isinstance(content, str) or len(content) > 12000:
                raise ValueError('Invalid extraction response')
            parsed = json.loads(content)
            memories = parsed.get('memory')
            if not isinstance(memories, list):
                raise ValueError('Invalid memory extraction schema')
            for item in memories:
                if not isinstance(item, dict) or not isinstance(item.get('text'), str):
                    raise ValueError('Invalid memory extraction item')
            from .runtime import SECRET
            parsed['memory'] = [item for item in memories if not SECRET.search(item['text'])][:4]
            return json.dumps(parsed, ensure_ascii=False)
        except (httpx.HTTPError, ValueError, KeyError):
            raise RuntimeError('Memory extraction temporarily unavailable') from None


def register():
    from mem0.configs.llms.base import BaseLlmConfig
    from mem0.utils.factory import EmbedderFactory, LlmFactory
    EmbedderFactory.provider_to_class['mgfr_cpu'] = 'mgfr_memory.providers.CpuEmbedding'
    LlmFactory.provider_to_class['mgfr_original'] = ('mgfr_memory.providers.OriginalVoiceLlm', BaseLlmConfig)
