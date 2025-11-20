@echo off
chcp 65001 >nul
REM CaseCheck One-Click Installation Tool

echo ========================================
echo CaseCheck One-Click Installation
echo ========================================
echo.
echo This will automatically install CaseCheck system
echo Please wait...
echo.

REM Check Python
echo [1/7] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found!
    echo.
    echo   Please install Python 3.8+ first:
    echo   https://www.python.org/downloads/
    echo.
    echo   IMPORTANT: Check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   [OK] Python %PYVER%

REM Create necessary directories
echo.
echo [2/7] Creating directories...
if not exist "data\database" mkdir "data\database" >nul 2>&1
if not exist "data\models" mkdir "data\models" >nul 2>&1
if not exist "data\logs" mkdir "data\logs" >nul 2>&1
if not exist "data\cases" mkdir "data\cases" >nul 2>&1
echo   [OK]

REM Upgrade pip
echo.
echo [3/7] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo   [OK]

REM Install dependencies
echo.
echo [4/7] Installing dependencies (2-3 minutes)...
echo   This may take a while, please be patient...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo   [WARNING] Some packages may have failed
    echo   Trying with verbose output...
    python -m pip install -r requirements.txt
)
echo   [OK]

REM Create .env file
echo.
echo [5/7] Creating configuration file...
if not exist ".env" (
    (
    echo # CaseCheck Configuration
    echo OPENAI_API_KEY=
    echo DEVICE=cpu
    echo DATABASE_PATH=data/database/cases.db
    echo VECTOR_DB_PATH=data/database/vectors
    echo MODEL_CACHE_DIR=data/models
    echo BGE_MODEL_NAME=BAAI/bge-m3
    echo API_HOST=0.0.0.0
    echo API_PORT=8000
    echo WEB_HOST=0.0.0.0
    echo WEB_PORT=8501
    echo LOG_LEVEL=INFO
    echo LOG_FILE=data/logs/app.log
    ) > .env
    echo   [OK] Created .env file
) else (
    echo   [OK] .env file already exists
)

REM Check data files
echo.
echo [6/7] Checking data files...
if exist "data\database\cases.db" (
    echo   [OK] Database: cases.db found
) else (
    echo   [WARNING] Database not found
)

if exist "data\database\vectors" (
    echo   [OK] Vector DB: vectors/ found
) else (
    echo   [WARNING] Vector database not found
)

if exist "data\theory_mapping.yaml" (
    echo   [OK] Theory mapping found
) else (
    echo   [WARNING] Theory mapping not found
)

REM Installation complete
echo.
echo [7/7] Installation complete!
echo   [OK]

echo.
echo ========================================
echo Installation Successful!
echo ========================================
echo.
echo System is ready to use!
echo.
echo NEXT STEP:
echo   Double-click "start_windows.bat" to start the system
echo.
echo IMPORTANT NOTES:
echo   - First startup will download BGE-M3 model (~600MB)
echo   - This takes 5-10 minutes depending on internet speed
echo   - Subsequent startups will be much faster
echo.
echo After startup, access:
echo   Web Interface: http://localhost:8501
echo   API Docs:      http://localhost:8000/docs
echo.
echo ========================================
pause
