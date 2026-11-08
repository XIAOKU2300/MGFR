from pathlib import Path
import subprocess
HERE=Path(__file__).resolve().parent
editor=HERE.parent/'Editor/Unity.exe'
log=HERE/'gpu-baseline.log'
if log.exists():raise RuntimeError('Log exists')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
child=subprocess.Popen([str(editor),'-batchmode','-noUpm','-force-d3d11','-projectPath',str(HERE/'GpuProbe-v1'),'-executeMethod','StereoGpuProbe.Run','-quit','-logFile',str(log)],startupinfo=startup)
try:code=child.wait(timeout=110)
except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned editor probe timed out') from None
print('GPU_PROBE_EDITOR_EXIT',code)
result=HERE/'Probe-baseline-v1/result.json'
if result.exists():print(result.read_text(encoding='utf-8-sig'))
else:print('No GPU result; see',log)
raise SystemExit(code)
