@echo off
REM 双击运行定时关机程序（需要已安装 Python 3）
cd /d "%~dp0"
start "" pythonw shutdown_timer.py
