@echo off
title Stop Jarvis
cd /d "%~dp0"

echo Stopping Jarvis...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' }; if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host '  Jarvis stopped.' -ForegroundColor Yellow } else { Write-Host '  Jarvis was not running.' -ForegroundColor Yellow }"

echo.
echo   It will start again next time you log in.
echo   To start it now, open Jarvis from your Desktop or Start menu.
echo.
pause
