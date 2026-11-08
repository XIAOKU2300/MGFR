@echo off
"H:\MGFR\dialogue-service\.venv\Scripts\python.exe" -B -X utf8 "%~dp0launch_candidate.py"
if errorlevel 1 pause
