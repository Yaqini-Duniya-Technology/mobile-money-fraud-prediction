@echo off

title FraudGuard AI API

cd /d "%~dp0"

echo.
echo ==========================================
echo       FraudGuard AI API
echo ==========================================
echo.
echo Starting FastAPI on:
echo http://127.0.0.1:8001
echo.
echo API documentation:
echo http://127.0.0.1:8001/docs
echo.
echo ==========================================
echo.

call C:\Users\ADMIN\anaconda3\Scripts\activate.bat

python -m uvicorn api.main:app --host 127.0.0.1 --port 8001

pause