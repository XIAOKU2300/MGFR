from pathlib import Path
import datetime,json,subprocess,sys
root=Path(__file__).resolve().parent
release=root.parent/'DialogueRenderRepair-20261020'
player=release/'Final-v3/Player/MGFR.exe'
output=root/('Review-menu-monitored-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));output.mkdir()
log=output/'player.log'
command=[str(player),'-batchmode','-mgfr-noxr','-force-d3d11','-mgfr-structured-voice','-mgfr-avatar-data',str(root.parent/'SiLLMBridge-20261020/MainData'),'-mgfr-service-url','ws://127.0.0.1:1/ws','-mgfr-action-port','1','-mgfr-skins','-mgfr-skin','swimsuit','-mgfr-zmd','-mgfr-wardrobe','-mgfr-shoes','-mgfr-hand-menu-review','-mgfr-hand-menu-out',str(output/'Results'),'-logFile',str(log)]
monitor=subprocess.Popen([sys.executable,str(release/'monitor_player.py'),'--log',str(log),'--',*command],cwd=player.parent,creationflags=subprocess.CREATE_NO_WINDOW)
code=monitor.wait(timeout=100)
exit_result=json.loads((output/'player-exit.json').read_text(encoding='utf-8'))
result=json.loads((output/'Results/result.json').read_text(encoding='utf-8-sig'))
print('MONITORED_MAIN_PLAYER_MENU',output,flush=True)
print(json.dumps({'monitorExit':code,'playerExit':exit_result,'review':result},ensure_ascii=False,indent=2),flush=True)
raise SystemExit(0 if code==0 and exit_result['exitCode']==0 and result.get('pass') else 5)
