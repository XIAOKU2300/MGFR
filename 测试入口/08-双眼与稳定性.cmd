@echo off
"H:\MGFR\dialogue-service\.venv\Scripts\python.exe" -B -X utf8 "H:\MGFR\DialogueRenderRepair-20261020\verify_stereo_current.py"
if errorlevel 1 pause
