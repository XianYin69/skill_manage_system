@echo off
rem sms-shell native launcher (Windows, ASCII only): cmd -> PowerShell DOS-style TUI, NO python for the shell itself. Args are passed as ONE quoted string because PowerShell 5.1 -File drops bare ":token" args. Fallback to python engine (bin/locate.py) only for: first arg "api" or PowerShell missing. Deploy = copy all bin files to target path.
chcp 65001 >nul
if /I "%~1"=="api" goto py
where /q powershell.exe
if errorlevel 1 goto py
if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0sms_shell.ps1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0sms_shell.ps1' @args" %*
)
exit /b %ERRORLEVEL%
:py
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python -B "%~dp0locate.py" %*
