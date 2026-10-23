@echo off
echo Running GuardianAI Backend Test Suite ...
cd /d "%~dp0"
python backend\tests\test_api.py
pause
