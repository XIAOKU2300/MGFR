from pathlib import Path
import runpy
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ORIGINAL=ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice_server.py'
sys.path.insert(0,str(HERE))
namespace=runpy.run_path(str(ORIGINAL),run_name='mgfr_original_private_bootstrap')
app=namespace['app']
@app.get('/avatar-health')
async def avatar_health():return {'revision':'json-emotion-actions-v1','jsonFirst':True,'voicePort':8774,'bridgePort':18766}
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=8774,log_level='warning',access_log=False)
