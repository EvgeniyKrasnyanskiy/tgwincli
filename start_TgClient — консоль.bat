@echo off

set PYTHONW_EXE=%~dp0venv\Scripts\python.exe
set SCRIPT_PATH=tgmain.pyw

start "" "%PYTHONW_EXE%" "%SCRIPT_PATH%"

