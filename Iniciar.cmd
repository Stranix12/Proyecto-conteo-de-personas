@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero ejecuta Preparar.cmd. Consulta los requisitos en README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_local.py
pause
