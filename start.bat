@echo off
chcp 65001 >nul
echo ========================================
echo   AI Knowledge Hub - 一键启动
echo   后端: http://localhost:8000  (自动重载)
echo   前端: http://localhost:5173  (热更新)
echo ========================================
echo.

echo [1/2] 启动后端 (FastAPI + reload) ...
start "AI-KB-Backend" cmd /k "cd /d %~dp0backend && python server.py"

echo [2/2] 启动前端 (Vite dev) ...
start "AI-KB-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo 已启动！浏览器打开 http://localhost:5173
echo 后端代码修改后自动重载，前端代码保存后热更新。
pause
