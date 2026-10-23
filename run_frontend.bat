@echo off
echo ========================================================
echo  Launching GuardianAI React Frontend
echo ========================================================
cd /d "%~dp0frontend"

:: Open the browser immediately
start http://localhost:5173

:: Start the Vite server if not already active
npm run dev
pause
