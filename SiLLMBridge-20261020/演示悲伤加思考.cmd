@echo off
"C:\Program Files\Python312\python.exe" -X utf8 "%~dp0demo_emotions.py" --emotion sad --action think
if errorlevel 1 pause
