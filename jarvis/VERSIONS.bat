@echo off
title Jarvis - versions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo   Jarvis is not installed in this folder.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" versions.py
