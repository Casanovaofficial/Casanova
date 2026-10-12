@echo off
title Install Jarvis
cd /d "%~dp0"

echo ==========================================================
echo   INSTALLING JARVIS
echo   This takes 10-20 minutes. Do not close this window.
echo ==========================================================
echo.

rem Remove the "downloaded from the internet" mark that blocks scripts
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Recurse | Unblock-File" 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows.ps1"

echo.
echo ==========================================================
echo   If there is RED text above, send Claude a screenshot.
echo.
echo   The floating mic panel should now be on screen, and
echo   Jarvis is on your Desktop and in your Start menu.
echo.
echo     Win + Alt + J     - talk from anywhere
echo     the gear          - settings, and how it behaves
echo     STOP_JARVIS.bat   - shut it down completely
echo     TEST_JARVIS.bat   - run it with the technical log visible
echo     CHECK_MIC.bat     - test the microphone
echo ==========================================================
echo.
pause
