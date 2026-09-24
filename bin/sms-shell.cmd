@echo off
rem sms-shell — Windows 启动入口：部署后把本 bin 目录加入 PATH 即可用 `sms-shell`
python -B "%~dp0..\scripts\shell.py" %*
