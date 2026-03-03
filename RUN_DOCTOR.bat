@echo off
cd /d "%~dp0"
py -3 ops\doctor.py --fix
pause
