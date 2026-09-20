@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" goto missing
".venv\Scripts\python.exe" -m bb84 experiments --preset standard --output results-standard --seed 84
if errorlevel 1 goto failed
echo.
echo Finished successfully. Experiment results: results-standard\report.html
goto finish
:missing
echo Run SETUP_WINDOWS.cmd first.
goto finish
:failed
echo The command failed. Read the error message above.
:finish
popd
pause