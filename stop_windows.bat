@echo off
chcp 65001 >nul

echo ========================================
echo CaseCheck System Stopping
echo ========================================
echo.

REM Kill by window title
taskkill /FI "WindowTitle eq CaseCheck-API*" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo API server stopped
) else (
    echo API server not running
)

taskkill /FI "WindowTitle eq CaseCheck-Web*" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo Web interface stopped
) else (
    echo Web interface not running
)

echo.
echo ========================================
echo Services Stopped
echo ========================================
echo.
pause
