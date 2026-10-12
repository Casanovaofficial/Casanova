@echo off
title Jarvis - Microphone Check
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo ERROR: Jarvis is not installed in this folder. Run INSTALL.bat first.
  echo.
  pause
  exit /b 1
)

echo Stopping Jarvis so it releases the microphone...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
timeout /t 2 /nobreak >nul

".venv\Scripts\python.exe" check_mic.py

echo.
echo Starting Jarvis again...
start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
timeout /t 2 /nobreak >nul
