@echo off
echo ========================================================
echo  Starting GuardianAI Full Stack (Backend + Frontend)
echo ========================================================

:: 1. Launch Backend in background cmd window
start "GuardianAI Backend API (Port 8000)" cmd /k "cd /d %~dp0 && python run_backend.py"

:: 2. Wait 2 seconds for backend to initialize
timeout /t 2 /nobreak >nul

:: 3. Launch Frontend and open browser
start "GuardianAI React Frontend (Port 5173)" cmd /k "cd /d %~dp0frontend && npm run dev"

:: 4. Also open Emergency Standalone Demo option
echo Full stack launched!
echo - React Frontend:  http://localhost:5173
echo - Backend API:     http://127.0.0.1:8000
echo - Emergency Demo:  %~dp0emergency-demo\index.html
pause
