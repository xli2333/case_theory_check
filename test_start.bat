@echo off
echo Testing start script...
echo.

echo [Step 1] Check Python
python --version
if errorlevel 1 (
    echo FAIL: Python not found
    pause
    exit /b 1
) else (
    echo PASS: Python found
)
echo.

echo [Step 2] Check .env
if exist .env (
    echo PASS: .env exists
) else (
    echo FAIL: .env missing
    pause
    exit /b 1
)
echo.

echo [Step 3] Check src directory
if exist src (
    echo PASS: src exists
) else (
    echo FAIL: src missing
    pause
    exit /b 1
)
echo.

echo [Step 4] Check API file
if exist src\api\main.py (
    echo PASS: API main.py exists
) else (
    echo FAIL: API main.py missing
    pause
    exit /b 1
)
echo.

echo [Step 5] Check Web file
if exist src\web\app.py (
    echo PASS: Web app.py exists
) else (
    echo FAIL: Web app.py missing
    pause
    exit /b 1
)
echo.

echo ========================================
echo All checks passed!
echo ========================================
echo.
echo Ready to start services.
echo.
pause
