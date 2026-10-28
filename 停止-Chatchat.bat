@echo off
chcp 65001 >nul
title 停止 Chatchat
"D:\miniconda\envs\chatchat\python.exe" "D:\chatchat-project\stop_all.py"
echo.
pause
