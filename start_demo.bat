@echo off
chcp 65001 >nul
REM ============================================================
REM CharacterSeed — 一键 Demo 启动脚本
REM ============================================================
REM 启动方式：双击运行此文件，或终端中执行 .\start_demo.bat
REM
REM 脚本职责：
REM   1. 启动 FastAPI 后端 (uvicorn on :8000)
REM   2. 等待后端就绪
REM   3. 启动 Streamlit 前端 (on :8501)
REM   4. 自动打开浏览器
REM
REM 停止方式：关闭两个弹出的终端窗口，或 Ctrl+C
REM ============================================================

echo ============================================================
echo   CharacterSeed Demo 启动中...
echo ============================================================
echo.
echo [1/3] 检查依赖...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [2/3] 启动 FastAPI 后端 (端口 8000)...
start "CharacterSeed-Backend" cmd /k "cd /d %~dp0 && uvicorn backend.main:app --reload --port 8000 --host 0.0.0.0"

echo [3/3] 等待后端就绪...
REM 轮询等待后端启动（最多 30 秒）
set /a count=0
:wait_loop
timeout /t 2 /nobreak >nul
set /a count+=2
curl -s http://localhost:8000/ >nul 2>&1
if %errorlevel% equ 0 goto backend_ready
if %count% geq 30 goto backend_timeout
goto wait_loop

:backend_timeout
echo [WARNING] 后端启动超时，仍然启动前端...
goto start_frontend

:backend_ready
echo [OK] 后端就绪！

:start_frontend
echo [4/4] 启动 Streamlit 前端 (端口 8501)...
echo 浏览器将自动打开 http://localhost:8501
start "CharacterSeed-Frontend" cmd /k "cd /d %~dp0 && streamlit run frontend/app.py"

REM 等待 Streamlit 启动后打开浏览器
timeout /t 5 /nobreak >nul
start "" http://localhost:8501

echo.
echo ============================================================
echo   Demo 已启动！
echo   后端: http://localhost:8000/docs
echo   前端: http://localhost:8501
echo   关闭后端/前端窗口即可停止
echo ============================================================
pause
