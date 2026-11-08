@echo off
"H:\MGFR\dialogue-service\.venv\Scripts\python.exe" -B -X utf8 "%~dp0launch_candidate.py" -mgfr-mr-original -mgfr-hand-envelope-original
if errorlevel 1 pause
