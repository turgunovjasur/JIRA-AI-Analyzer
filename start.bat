@echo off
setlocal enabledelayedexpansion
title JIRA AI Analyzer

echo.
echo ============================================================
echo   JIRA AI Analyzer - Ishga tushirish
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [XATO] Virtual environment topilmadi!
    echo        Avval setup.bat ni ishga tushiring.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [XATO] .env fayl topilmadi!
    echo        .env faylini to'ldiring.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [XATO] Frontend dependency topilmadi!
    echo        Avval: cd frontend ^&^& npm install
    pause
    exit /b 1
)

set START_WORKER=0
set WEBHOOK_EXECUTION_MODE=%APP_WEBHOOK_EXECUTION_MODE%
if "%WEBHOOK_EXECUTION_MODE%"=="" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="APP_WEBHOOK_EXECUTION_MODE" (
            set WEBHOOK_EXECUTION_MODE=%%b
        )
    )
)
if /i "%WEBHOOK_EXECUTION_MODE%"=="queue" (
    set START_WORKER=1
)
if "%WEBHOOK_EXECUTION_MODE%"=="" (
    set WEBHOOK_EXECUTION_MODE=inline
)

set LOCAL_IP=127.0.0.1
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set TMP_IP=%%a
    set TMP_IP=!TMP_IP: =!
    if not "!TMP_IP!"=="127.0.0.1" (
        set LOCAL_IP=!TMP_IP!
    )
)

echo  UI  (Next.js)   : http://!LOCAL_IP!:3000
echo  API (FastAPI)   : http://!LOCAL_IP!:8000
echo  Mode            : %WEBHOOK_EXECUTION_MODE%
echo  Localhost UI    : http://localhost:3000
echo.
echo  Ctrl+C bosib to'xtatish mumkin
echo.

start "Backend API :8000" cmd /k ".venv\Scripts\python.exe -m uvicorn services.webhook.jira_webhook_handler:app --host 0.0.0.0 --port 8000"

if "%START_WORKER%"=="1" (
    start "Background Worker" cmd /k ".venv\Scripts\python.exe -m services.worker.main"
)

timeout /t 3 /nobreak >nul

echo [WEB] Next.js ishga tushmoqda...
cd frontend
set BACKEND_API_BASE_URL=http://127.0.0.1:8000
set NEXT_PUBLIC_BACKEND_API_BASE_URL=http://127.0.0.1:8000
call npm run dev -- --hostname 0.0.0.0 --port 3000

pause
endlocal
