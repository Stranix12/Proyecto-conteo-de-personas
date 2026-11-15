@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Crea primero el entorno: python -m venv .venv
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_local.py
pause
