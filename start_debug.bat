@echo off
chcp 65001 >nul

echo ========================================
echo CaseCheck System Starting (Debug Mode)
echo ========================================
echo.
echo Current Directory: %CD%
echo.

REM Check Python
echo [Check 1] Testing Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
) else (
    echo PASS: Python OK
)
echo.

REM Check .env
echo [Check 2] Testing .env file...
if not exist .env (
    echo ERROR: .env not found
    echo Creating .env file...
    echo Please run install script first
    pause
    exit /b 1
) else (
    echo PASS: .env exists
)
echo.

REM Check src
echo [Check 3] Testing src directory...
if not exist src (
    echo ERROR: src directory not found
    pause
    exit /b 1
) else (
    echo PASS: src directory exists
)
echo.

REM Check API file
echo [Check 4] Testing API file...
if not exist src\api\main.py (
    echo ERROR: API file not found
    pause
    exit /b 1
) else (
    echo PASS: API file exists
)
echo.

REM Check Web file
echo [Check 5] Testing Web file...
if not exist src\web\app.py (
    echo ERROR: Web file not found
    pause
    exit /b 1
) else (
    echo PASS: Web file exists
)
echo.

echo ========================================
echo All checks passed! Starting services...
echo ========================================
echo.

REM Start API
echo Starting API server...
echo Command: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
start "CaseCheck-API" cmd /k "cd /d %CD% && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
echo API window opened
echo.

REM Wait
echo Waiting 10 seconds for API to initialize...
timeout /t 10 /nobreak
echo.

REM Start Web
echo Starting Web interface...
echo Command: streamlit run src/web/app.py --server.port 8501 --server.address 0.0.0.0
start "CaseCheck-Web" cmd /k "cd /d %CD% && streamlit run src/web/app.py --server.port 8501 --server.address 0.0.0.0"
echo Web window opened
echo.

REM Wait
echo Waiting 5 seconds for Web to initialize...
timeout /t 5 /nobreak
echo.

echo ========================================
echo Services Started Successfully!
echo ========================================
echo.
echo You should see 2 new command windows:
echo   1. CaseCheck-API (port 8000)
echo   2. CaseCheck-Web (port 8501)
echo.
echo Access URLs:
echo   Web Interface: http://localhost:8501
echo   API Docs:      http://localhost:8000/docs
echo.
echo Opening browser in 3 seconds...
timeout /t 3 /nobreak
start http://localhost:8501
echo.

echo ========================================
echo This window can be closed now.
echo The services are running in the other 2 windows.
echo ========================================
echo.
pause
