@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
py -3 -m venv .venv
if not errorlevel 1 goto install
python -m venv .venv
if errorlevel 1 goto missing
:install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Setup complete. Run RUN_DEMO.cmd, RUN_EXPERIMENTS.cmd or RUN_TESTS.cmd.
echo Optional: .venv\Scripts\python.exe -m pip install -r requirements-optional.txt
goto finish
:missing
echo Install Python 3.12 from python.org, then run this file again.
goto finish
:failed
echo Installation failed. Read the message above and check your Internet connection.
:finish
popd
pause