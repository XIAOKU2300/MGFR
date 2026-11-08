from pathlib import Path
HERE=Path(__file__).resolve().parent
def create(path,text):
    with path.open('x',encoding='utf-8') as stream:stream.write(text)
source=(HERE/'test_cloth_scale.py').read_text(encoding='utf-8').replace('Final-v2/Player','Final-v3/Player')
source=source.replace('import subprocess','import subprocess\nimport sys')
source=source.replace('startup=subprocess.STARTUPINFO()',"if '--baseline' in sys.argv:cmd+=['-mgfr-scale-old-metric']\nstartup=subprocess.STARTUPINFO()")
create(HERE/'test_scale_final.py',source)
for old,new in [('test_unity_voice.py','test_voice_final_player.py'),('test_render_final.py','test_material_final_player.py')]:
    source=(HERE/old).read_text(encoding='utf-8').replace("'Current/Player/MGFR.exe'","'Final-v3/Player/MGFR.exe'").replace("ROOT/'Current/Voice'","ROOT/'Final-v3/Voice'")
    create(HERE/new,source)
source=(HERE/'launch_current.py').read_text(encoding='utf-8').replace("HERE / 'Current'","HERE / 'Final-v3'")
create(HERE/'launch_final.py',source)
create(HERE/'启动本次修复.cmd','@echo off\n"H:\\MGFR\\dialogue-service\\.venv\\Scripts\\python.exe" -B -X utf8 "H:\\MGFR\\DialogueRenderRepair-20261020\\launch_final.py"\nif errorlevel 1 pause\n')
for name in ['test_motion.py','test_catalog.py']:
    source=(HERE.parent/'NativeMotionAdapt-20261020'/name).read_text(encoding='utf-8').replace("default='Current'","default='Final-v3'")
    # Keep reports compact; diagnostics remain in the player log.
    source=source.replace("else:print((output/'player.log').read_text(encoding='utf-8-sig',errors='replace')[-6000:])", "else:print('No result; diagnostic log:',str(output/'player.log'))")
    create(HERE/name,source)
print('Final entry and checks point to Final-v3.')
