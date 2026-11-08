from pathlib import Path
HERE = Path(__file__).resolve().parent
def create(path, text):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(text)

source = (HERE / 'launch_repaired.py').read_text(encoding='utf-8')
source = source.replace("HERE / 'Release-v1'", "HERE / 'Current'")
source = source.replace('VOICE_PORT = 8774', 'VOICE_PORT = 8775').replace('ACTION_PORT = 18767', 'ACTION_PORT = 18768')
source = source.replace('structured-history-recovery-v2', 'structured-history-name-readback-v3')
source = source.replace('from install_voice_v2 import install', 'from install_voice_v3 import install')
create(HERE / 'launch_main.py', source)
create(HERE / '启动修复版.cmd', '@echo off\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -B -X utf8 "H:\\MGFR\\DialogueRenderRepair-20261020\\launch_main.py"\nif errorlevel 1 pause\n')
source = (HERE / 'Voice/test_live_worker.py').read_text(encoding='utf-8').replace('127.0.0.1:8774', '127.0.0.1:8775').replace('live-worker-', 'live-final-')
create(HERE / 'Voice/test_live_final.py', source)
source = (HERE / 'Voice/test_recovery_v2.py').read_text(encoding='utf-8')
source = source.replace('[str(SERVICE), str(HERE)]', "[str(SERVICE), str(ROOT / 'DialogueRenderRepair-20261020/Current/Voice'), str(HERE)]")
source = source.replace('import install_voice_v2', 'import install_voice_v3').replace('install_voice_v2.install', 'install_voice_v3.install')
source = source.replace("if user == 'retry'", "if user == 'timeout':\n                raise TimeoutError('local fixture timeout')\n            if user == 'retry'")
source = source.replace("['normal', 'retry', 'normal', 'exhaust', 'normal']", "['normal', 'retry', 'normal', 'exhaust', 'normal', 'timeout', 'normal']")
source = source.replace("if prompt == 'exhaust':", "if prompt in ('exhaust', 'timeout'):")
source = source.replace("'recovery-'", "'recovery-final-'")
create(HERE / 'Voice/test_final_recovery.py', source)
source = (HERE / 'test_render_release.py').read_text(encoding='utf-8').replace('Release-v1/Player', 'Current/Player')
create(HERE / 'test_render_final.py', source)
print('Prepared final launch and checks; existing entries preserved.')
