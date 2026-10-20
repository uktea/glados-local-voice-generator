@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  python -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe setup_models.py
if errorlevel 1 goto fail
echo Setup complete. Run Start.cmd
pause
exit /b 0
:fail
echo Setup failed. See the error above.
pause
exit /b 1
