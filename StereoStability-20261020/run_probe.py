from pathlib import Path
import subprocess
import sys
root = Path(__file__).resolve().parent
method, logname = sys.argv[1:3]
log = root / logname
if log.exists():
    raise RuntimeError('Refusing to replace an existing diagnostic log')
startup = subprocess.STARTUPINFO()
startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startup.wShowWindow = 0
project = sys.argv[3] if len(sys.argv)>3 else 'GpuProbe-v1'
command = [str(root.parent / 'Editor/Unity.exe'), '-batchmode', '-noUpm', '-force-d3d11', '-projectPath', str(root/project), '-executeMethod', method, '-quit', '-logFile', str(log)]
if project in ('ShaderProject-v1', 'ShaderProject-xr-v2'):
    command.remove('-noUpm')
child = subprocess.Popen(command, startupinfo=startup)
try:
    code = child.wait(timeout=180)
except subprocess.TimeoutExpired:
    child.terminate()
    child.wait(timeout=10)
    raise RuntimeError('Owned GPU probe timed out') from None
print('EDITOR_EXIT', code, 'LOG', str(log))
raise SystemExit(code)
