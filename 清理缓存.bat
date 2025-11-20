@echo off
echo ========================================
echo 正在清理所有缓存...
echo ========================================
echo.

echo [1/4] 清理 Python 缓存文件...
del /s /q *.pyc 2>nul
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
echo Python 缓存清理完成!

echo.
echo [2/4] 清理 Streamlit 缓存...
if exist ".streamlit\cache" (
    rd /s /q ".streamlit\cache"
    echo Streamlit 缓存清理完成!
) else (
    echo 无 Streamlit 缓存需要清理
)

echo.
echo [3/4] 清理临时文件...
if exist "*.tmp" del /q *.tmp 2>nul
if exist "*.log" del /q *.log 2>nul
echo 临时文件清理完成!

echo.
echo [4/4] 关闭所有运行中的服务...
taskkill /f /im python.exe /fi "WINDOWTITLE eq API*" 2>nul
taskkill /f /im python.exe /fi "WINDOWTITLE eq Web*" 2>nul
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo 缓存清理完成!
echo 请使用 "简易启动.bat" 重新启动服务
echo ========================================
echo.
pause
