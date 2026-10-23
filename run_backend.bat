@echo off
echo Starting GuardianAI Backend on http://127.0.0.1:8000 ...
cd /d "%~dp0"
python run_backend.py
pause
