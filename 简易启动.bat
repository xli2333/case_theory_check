@echo off
echo Starting CaseCheck...
echo.

echo Starting API...
start "API" cmd /k "cd /d %~dp0 && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"

timeout /t 8 /nobreak

echo Starting Web...
start "Web" cmd /k "cd /d %~dp0 && streamlit run src/web/app.py --server.port 8501 --server.address 0.0.0.0"

timeout /t 5 /nobreak

echo.
echo Opening browser...
start http://localhost:8501

echo.
echo Services started!
echo Close the API and Web windows to stop.
echo.
pause
