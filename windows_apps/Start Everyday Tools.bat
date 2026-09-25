@echo off
cd /d "%~dp0\.."
py -3 -m windows_apps %*
if errorlevel 1 pause
