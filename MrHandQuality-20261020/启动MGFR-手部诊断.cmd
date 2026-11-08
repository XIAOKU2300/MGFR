@echo off
"H:\MGFR\dialogue-service\.venv\Scripts\python.exe" -B -X utf8 "%~dp0launch_candidate.py" -mgfr-hand-diagnostics "%~dp0Review\HeadsetTrace"
if errorlevel 1 pause
