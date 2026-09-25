@echo off
rem sms-shell launcher (Windows): python sms-shell.py (Textual TUI preferred, ps1 fallback); api -> locate.py.
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if /I "%~1"=="api" goto py
python -B "%~dp0sms-shell.py" %*
if errorlevel 0 exit /b %ERRORLEVEL%
:py
python -B "%~dp0locate.py" %*
