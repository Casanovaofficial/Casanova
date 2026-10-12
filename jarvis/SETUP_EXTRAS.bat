@echo off
title Jarvis - install the good stuff
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo   Jarvis is not installed here. Run INSTALL.bat first.
  pause
  exit /b 1
)

echo ==========================================================
echo   Adding: screen clicking, Word documents, natural voice
echo   and GPU speech. Takes a few minutes, needs internet.
echo ==========================================================
echo.

echo [1/4] Screen control, so it can click things...
".venv\Scripts\python.exe" -m pip install -q uiautomation

echo [2/4] Word document support...
".venv\Scripts\python.exe" -m pip install -q python-docx

echo [3/4] Natural voice engine...
".venv\Scripts\python.exe" -m pip install -q piper-tts
".venv\Scripts\python.exe" get_voice.py alan

echo [4/4] GPU speech recognition (about 700 MB)...
".venv\Scripts\python.exe" -m pip install -q nvidia-cublas-cu12 nvidia-cudnn-cu12

echo.
echo Restarting Jarvis...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul
timeout /t 3 /nobreak >nul
start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"

echo.
echo ==========================================================
echo   Done. Jarvis now has a British voice, can click
echo   anything on screen, and transcribes on the GPU.
echo ==========================================================
echo.
pause
