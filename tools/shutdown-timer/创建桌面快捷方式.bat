@echo off
chcp 65001 >nul
REM 双击在桌面创建「定时关机」快捷方式（需要已安装 Python 3）
cd /d "%~dp0"
python shutdown_timer.py --shortcut
pause
