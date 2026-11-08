@echo off
cd /d "F:\GPT-SoVITS\GPT-SoVITS-v2pro-20250604-nvidia50\GPT-SoVITS-v2pro-20250604-nvidia50"
set "PATH=%CD%\runtime;%PATH%"
runtime\python.exe -I -B -X utf8 si_voice_20261018\serve_si.py --model 00 --port 9880
pause
