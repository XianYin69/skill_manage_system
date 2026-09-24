@echo off
rem sms-shell launcher (Windows). Deploy = copy bin files to target path; locate.py resolves the installed skill_manage_system.
python -B "%~dp0locate.py" %*
