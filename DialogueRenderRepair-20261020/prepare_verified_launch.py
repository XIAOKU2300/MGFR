from pathlib import Path
HERE = Path(__file__).resolve().parent
def create(path, text):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(text)
source=(HERE/'launch_main.py').read_text(encoding='utf-8').replace('VOICE_PORT = 8775','VOICE_PORT = 8776').replace('ACTION_PORT = 18768','ACTION_PORT = 18769').replace('structured-history-name-readback-v3','structured-history-natural-clauses-v4').replace('from install_voice_v3 import install','from install_voice_v4 import install')
create(HERE/'launch_current.py',source)
source=(HERE/'Voice/test_live_final.py').read_text(encoding='utf-8').replace('127.0.0.1:8775','127.0.0.1:8776').replace('live-final-','live-current-')
create(HERE/'Voice/test_live_current.py',source)
source=(HERE/'Voice/probe_reply_readback.py').read_text(encoding='utf-8').replace('from install_voice_v3 import install','from install_voice_v4 import install')
create(HERE/'Voice/probe_current_readback.py',source)
source=(HERE/'Voice/test_final_recovery.py').read_text(encoding='utf-8').replace('install_voice_v3','install_voice_v4').replace('recovery-final-','recovery-current-')
create(HERE/'Voice/test_current_recovery.py',source)
print('Prepared corrected natural-clause voice entry.')
