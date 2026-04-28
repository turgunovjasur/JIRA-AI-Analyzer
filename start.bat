@echo off
setlocal enabledelayedexpansion
title JIRA AI Analyzer

echo.
echo ============================================================
echo   JIRA AI Analyzer - Ishga tushirish
echo ============================================================
echo.

:: Virtual environment tekshirish
if not exist ".venv\Scripts\python.exe" (
    echo [XATO] Virtual environment topilmadi!
    echo        Avval setup.bat ni ishga tushiring.
    pause
    exit /b 1
)

:: .env tekshirish
if not exist ".env" (
    echo [XATO] .env fayl topilmadi!
    echo        .env faylini to'ldiring.
    pause
    exit /b 1
)

:: Tarmoq IP aniqlash
set LOCAL_IP=127.0.0.1
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set TMP_IP=%%a
    set TMP_IP=!TMP_IP: =!
    if not "!TMP_IP!"=="127.0.0.1" (
        set LOCAL_IP=!TMP_IP!
    )
)

echo  UI  (Streamlit) : http://!LOCAL_IP!:8501
echo  API (Webhook)   : http://!LOCAL_IP!:8000
echo  Localhost UI    : http://localhost:8501
echo.
echo  Ctrl+C bosib to'xtatish mumkin
echo.

:: Webhook serverni alohida oynada ishga tushirish
start "Webhook Server :8000" cmd /k ".venv\Scripts\python.exe -m uvicorn services.webhook.jira_webhook_handler:app --host 0.0.0.0 --port 8000"

:: 3 soniya kutish
timeout /t 3 /nobreak >nul

:: Streamlit UI
echo [UI] Streamlit ishga tushmoqda...
.venv\Scripts\python.exe -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false

pause
endlocal