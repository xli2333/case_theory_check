@echo off
echo ========================================
echo 完整重启系统（清理缓存+重启服务）
echo ========================================
echo.

echo [步骤 1/4] 关闭所有Python服务...
taskkill /f /im python.exe 2>nul
timeout /t 2 /nobreak >nul
echo 服务已关闭!

echo.
echo [步骤 2/4] 清理Python缓存...
del /s /q *.pyc 2>nul
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
echo Python缓存已清理!

echo.
echo [步骤 3/4] 清理Streamlit缓存...
if exist ".streamlit\cache" (
    rd /s /q ".streamlit\cache"
    echo Streamlit缓存已清理!
) else (
    echo 无Streamlit缓存需要清理
)

echo.
echo [步骤 4/4] 启动服务...
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo 正在启动API服务...
echo ========================================
start "API" cmd /k "cd /d %~dp0 && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"

timeout /t 8 /nobreak

echo.
echo ========================================
echo 正在启动Web服务...
echo ========================================
start "Web" cmd /k "cd /d %~dp0 && streamlit run src/web/app.py --server.port 8501 --server.address 0.0.0.0"

timeout /t 5 /nobreak

echo.
echo ========================================
echo 正在打开浏览器...
echo ========================================
start http://localhost:8501

echo.
echo ========================================
echo 系统已成功启动!
echo.
echo 重要提示:
echo 1. 请在浏览器中按 Ctrl+Shift+R 强制刷新页面
echo 2. 如果仍显示旧内容，请清理浏览器缓存
echo 3. 关闭API和Web窗口即可停止服务
echo ========================================
echo.
pause
