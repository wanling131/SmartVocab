@echo off
echo Starting SmartVocab Server...
start /b D:\Python\python.exe main.py
timeout /t 5 /nobreak >nul
echo Opening browser...
start http://localhost:5000
echo Server running. Close this window to stop.
pause