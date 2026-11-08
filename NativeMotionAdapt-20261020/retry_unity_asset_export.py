from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parent
project=ROOT/'UnityAssets-v1';log=project/'export-no-upm.log'
if log.exists() or (project/'asset-export.txt').exists():raise RuntimeError('Fresh export log and asset destination required')
args=[str(ROOT.parent/'Editor/Unity.exe'),'-batchmode','-nographics','-noUpm','-projectPath',str(project),'-executeMethod','NativeAssetExporter.Export','-quit','-logFile',str(log)]
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
child=subprocess.Popen(args,startupinfo=startup)
try:code=child.wait(timeout=150)
except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10);raise RuntimeError('Owned asset export timed out') from None
print('assetExportExit',code)
report=project/'asset-export.txt'
if report.exists():print(report.read_text(encoding='utf-8-sig'))
else:
    lines=log.read_text(encoding='utf-8-sig',errors='replace').splitlines()
    for line in lines:
        if any(key in line for key in ['error CS','Failed to resolve packages','Exception:','NATIVE_UNITY_ASSETS_EXPORTED','executeMethod']):print(line[:250])
