"""Use the original private startup unchanged, with the new local app code.

The original bootstrap alone loads its credential and config. No credential is
copied into this candidate, printed or exposed through command arguments.
"""
from pathlib import Path
import runpy
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice_server.py'
sys.path.insert(0,str(HERE))
namespace=runpy.run_path(str(ORIGINAL),run_name='mgfr_original_private_bootstrap')

if __name__=='__main__':
    import uvicorn
    uvicorn.run(namespace['app'],host='127.0.0.1',port=8773,log_level='warning',access_log=False)
