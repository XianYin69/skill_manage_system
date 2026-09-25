@echo off
rem sms-shell launcher (Windows, ASCII only). Merged entry: plain args = interactive shell; first arg "api" = format API (formerly sms-api). Deploy = copy bin files to target path; locate.py resolves the installed skill_manage_system. UTF-8 codepage + PYTHONUTF8 = native Chinese.
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python -B "%~dp0locate.py" %*
