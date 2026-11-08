"""Internal additions to launch_voice_v6; retains the original voice app/config."""
from pathlib import Path
import importlib.util
import json
import runpy
import sys
import threading

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
RESOURCES = ROOT / 'SiLLMBridge-20261020'
REVISION = 'original-entry-json-actions-v1'


def load_module(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def install(app):
    import app as app_package
    from app import pipeline
    from app.engines import llm_openai
    if not Path(app_package.__file__).resolve().is_relative_to(SERVICE):
        raise RuntimeError('Existing voice app was not loaded from VoiceService10')
    if getattr(app.state, 'avatar_revision', None) == REVISION:
        return
    load_module('app.mgfr_avatar_json', HERE / 'avatar_json.py')
    adapted = load_module('app.mgfr_avatar_pipeline', HERE / 'avatar_pipeline.py')
    # Keep the original synthesis/audio framing and all ASR/cancellation code.
    adapted._speak = pipeline._speak
    pipeline._think_and_speak = adapted._think_and_speak

    original_llm = llm_openai.OpenAiCompatLlm

    class JsonRequestClient:
        def __init__(self, client):
            self.client = client

        def stream(self, method, url, **kwargs):
            payload = dict(kwargs['json'])
            payload['response_format'] = {'type': 'json_object'}
            kwargs['json'] = payload
            return self.client.stream(method, url, **kwargs)

    class JsonReplyLlm(original_llm):
        def _get_client(self):
            return JsonRequestClient(super()._get_client())

    llm_openai.OpenAiCompatLlm = JsonReplyLlm
    for route in app.routes:
        if getattr(route, 'path', None) == '/health':
            original_health = route.endpoint

            async def health():
                result = await original_health()
                result['avatarRevision'] = REVISION
                result['avatarBridgePort'] = 18766
                return result

            route.endpoint = health
            route.dependant.call = health
            break
    else:
        raise RuntimeError('Existing health route missing')
    app.state.avatar_revision = REVISION


def run_voice_worker():
    # The original bootstrap still owns private config/credentials and model paths.
    sys.path.insert(0, str(SERVICE))
    namespace = runpy.run_path(str(SERVICE / 'voice_server.py'), run_name='mgfr_existing_voice_bootstrap')
    app = namespace['namespace']['app']
    install(app)
    sys.path.append(str(RESOURCES))
    from main_bridge_final import make_server
    catalog = json.loads((RESOURCES / 'MainData/catalog.json').read_text(encoding='utf-8'))
    server = make_server(catalog, 18766)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name='avatar-local-interface')
    thread.start()
    try:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=8773, log_level='warning', access_log=False)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
