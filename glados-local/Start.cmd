@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe app.py
) else (
  echo Please run Setup.cmd first.
)
pause
