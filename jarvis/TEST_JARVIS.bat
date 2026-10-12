@echo off
title Jarvis - TEST WINDOW
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Jarvis is not installed in this folder. Run INSTALL.bat first.
  echo.
  pause
  exit /b 1
)

echo Stopping the background copy so this one can use the microphone...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo ==========================================================
echo   DIAGNOSTIC MODE
echo.
echo   The control window opens, AND this black window shows
echo   the raw technical log behind it. If Jarvis crashes, the
echo   reason appears here.
echo.
echo   Close this window to stop Jarvis.
echo ==========================================================
echo.

".venv\Scripts\python.exe" main.py

echo.
echo Jarvis stopped. If there is an error above, screenshot it.
pause
