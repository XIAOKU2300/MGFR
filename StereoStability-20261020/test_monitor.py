from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parent
out=root/'Monitor-check';out.mkdir()
for code in (0,7):
    log=out/f'child-{code}.log'
    result=subprocess.run([sys.executable,str(root/'monitor_player.py'),'--log',str(log),'--',sys.executable,'-c',f'import sys;sys.exit({code})'],check=True,timeout=15)
    report=json.loads((out/f'child-{code}-exit.json').read_text(encoding='utf-8'))
    assert report['exitCode']==code
    assert report['exitClass']==('normal' if code==0 else 'abnormal')
print('PROCESS_EXIT_MONITOR_PASS normal=0 abnormal=7')
