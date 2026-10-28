@echo off
chcp 65001 >nul
title Langchain-Chatchat
set CHATCHAT_ROOT=D:\chatchat-data

echo ============================================
echo   Langchain-Chatchat 启动器
echo   数据目录: %CHATCHAT_ROOT%
echo ============================================
echo.

rem ---- 1. 确保 Ollama 在跑（向量模型 bge-m3 依赖它）----
curl -s -o nul --max-time 3 http://127.0.0.1:11434/api/tags
if errorlevel 1 (
    echo [1/2] Ollama 未运行，正在后台启动...
    start "" /min ollama serve
    timeout /t 6 >nul
) else (
    echo [1/2] Ollama 已在运行
)

rem ---- 2. 启动 API + WebUI ----
rem 注意：这里不用 `chatchat start -a`。它内部用 multiprocessing(spawn) 起子进程，
rem 子进程不继承源码目录，实测 8501 起不来且没有任何报错。
rem run_all.py 用 subprocess 显式拉起两个脚本，20 秒双端口就绪。
echo [2/2] 正在启动 API + WebUI ...
echo.
echo   WebUI : http://127.0.0.1:8501
echo   API   : http://127.0.0.1:7861/docs
echo.
echo   停止：按 Ctrl+C，或双击 停止-Chatchat.bat
echo ============================================
echo.

"D:\miniconda\envs\chatchat\python.exe" "D:\chatchat-project\run_all.py"

if errorlevel 1 (
    echo.
    echo 启动失败，请把上面的报错发给我。
    pause
)
