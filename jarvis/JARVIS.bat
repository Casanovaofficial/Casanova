@echo off
title Jarvis
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo.
  echo   Jarvis is not installed in this folder yet.
  echo   Run INSTALL.bat first.
  echo.
  pause
  exit /b 1
)

rem If Jarvis is already running this just brings its window to the front.
start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
exit /b 0
