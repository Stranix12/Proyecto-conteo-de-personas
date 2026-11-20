@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto instalar
py -3.11 -m venv .venv
if errorlevel 1 (
  echo No se pudo crear el entorno. Instala Python 3.11 con el lanzador py.
  pause
  exit /b 1
)
:instalar
".venv\Scripts\python.exe" scripts\prepare.py
if errorlevel 1 (
  pause
  exit /b 1
)
pause
