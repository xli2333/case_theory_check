@echo off
chcp 65001 >nul

echo ========================================
echo CaseCheck System Starting
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.8+
    pause
    exit /b 1
)

echo Python OK
echo.

REM Check installation
if not exist .env (
    echo ERROR: System not installed
    echo Please run: 一键安装.bat
    pause
    exit /b 1
)

echo Installation OK
echo.

REM Start API
echo Starting API server...
start "CaseCheck-API" cmd /k python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

REM Wait
echo Waiting for API...
timeout /t 8 /nobreak >nul

REM Start Web
echo Starting Web interface...
start "CaseCheck-Web" cmd /k streamlit run src/web/app.py --server.port 8501 --server.address 0.0.0.0

REM Wait
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo Services Started
echo ========================================
echo.
echo Web: http://localhost:8501
echo API: http://localhost:8000/docs
echo.

REM Open browser
timeout /t 3 /nobreak >nul
start http://localhost:8501

echo Press any key to close...
pause >nul
