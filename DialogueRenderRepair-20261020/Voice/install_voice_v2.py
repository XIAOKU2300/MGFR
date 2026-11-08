"""Install the corrected adapter in an isolated worker using original private config."""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SERVICE = ROOT / 'SpeechNatural-20261019/VoiceService10'
REVISION = 'structured-history-recovery-v2'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def install(app, bridge_url):
    if getattr(app.state, 'conversation_repair', None) == REVISION:
        return
    sys.path.insert(0, str(ROOT / 'SpeechNatural-20261019/VoiceRepair'))
    adapter = load('app.mgfr_avatar_json', HERE / 'avatar_json_v2.py')
    adapter.URL = bridge_url
    load('app.mgfr_avatar_pipeline', HERE / 'avatar_pipeline_v2.py')
    import avatar_upgrade
    avatar_upgrade.REVISION = REVISION
    avatar_upgrade.install(app)
    app.state.conversation_repair = REVISION
    return adapter
