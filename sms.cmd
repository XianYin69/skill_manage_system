@echo off
rem sms.cmd - Windows entry shim (ASCII only: codepage 936 would corrupt CJK comments)
python -B "%~dp0sms.py" %*
