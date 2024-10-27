@echo off
set current_dir=%~dp0

cd "%current_dir%src"

python main.py

REM 防止窗口立即关闭
pause
