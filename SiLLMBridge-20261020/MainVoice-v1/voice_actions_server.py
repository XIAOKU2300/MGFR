from pathlib import Path
import runpy
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
try:
 namespace=runpy.run_path(str(ROOT/'HandLab-20261018/ChatLab-20261018/Project-Final/VoiceService/voice_server.py'),run_name='mgfr_original_private_bootstrap')
 from app import pipeline
 if not Path(pipeline.__file__).resolve().is_relative_to(HERE):raise RuntimeError('Wrong voice module')
 app=namespace['app']
 @app.get('/avatar-health')
 async def avatar_health():return {'revision':'json-emotion-actions-v1','jsonFirst':True,'voicePort':8774,'bridgePort':18766}
 if __name__=='__main__':
  import uvicorn
  uvicorn.run(app,host='127.0.0.1',port=8774,log_level='warning',access_log=False)
except Exception as error:
 print('Structured voice startup failed ('+type(error).__name__+').',file=sys.stderr)
 raise SystemExit(1)
