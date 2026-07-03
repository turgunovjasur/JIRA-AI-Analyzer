@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title QA-Assistant - Start

:: Portlarni o'zgartirish kerak bo'lsa shu yerda:
set BACKEND_PORT=8000
set FRONTEND_PORT=3000

echo.
echo ============================================================
echo   QA-Assistant - Ishga tushirish (production)
echo ============================================================
echo.

:: ---------- Tekshiruvlar ----------
if not exist ".venv\Scripts\python.exe" (
    echo [XATO] Virtual environment topilmadi! Avval setup.bat ni ishga tushiring.
    pause
    exit /b 1
)
if not exist ".env" (
    echo [XATO] .env fayl topilmadi! .env.example dan nusxa olib to'ldiring.
    pause
    exit /b 1
)
if not exist "frontend\.next\standalone\server.js" (
    echo [XATO] Frontend build topilmadi! Avval setup.bat ni ishga tushiring.
    pause
    exit /b 1
)

:: ---------- PostgreSQL tekshiruvi ----------
echo [DB] PostgreSQL ulanishi tekshirilmoqda...
.venv\Scripts\python.exe -c "import os;from dotenv import load_dotenv;load_dotenv();import psycopg;dsn=os.getenv('APP_POSTGRES_DSN','').strip();assert dsn,'APP_POSTGRES_DSN .env da bosh';psycopg.connect(dsn,connect_timeout=5).close()"
if %errorlevel% neq 0 (
    echo.
    echo [XATO] PostgreSQL ulanmayapti!
    echo        1^) PostgreSQL servisi ishlab turibdimi? ^(services.msc^)
    echo        2^) .env dagi APP_POSTGRES_DSN to'g'rimi?
    echo        3^) Baza yaratilganmi? ^(DEPLOY_WINDOWS.md ga qarang^)
    pause
    exit /b 1
)
echo [OK] PostgreSQL ulandi

:: ---------- Webhook rejimini .env dan o'qish ----------
set WEBHOOK_EXECUTION_MODE=%APP_WEBHOOK_EXECUTION_MODE%
if "%WEBHOOK_EXECUTION_MODE%"=="" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="APP_WEBHOOK_EXECUTION_MODE" set WEBHOOK_EXECUTION_MODE=%%b
    )
)
if "%WEBHOOK_EXECUTION_MODE%"=="" set WEBHOOK_EXECUTION_MODE=inline
set START_WORKER=0
if /i "%WEBHOOK_EXECUTION_MODE%"=="queue" set START_WORKER=1

:: ---------- Bind host (xavfsizlik: default faqat localhost) ----------
:: Servislar default 127.0.0.1 ga bog'lanadi — tashqaridan kirib bo'lmaydi.
:: LAN kirish kerak bo'lsa (FAQAT firewall ortida): .env ga APP_BIND_HOST=0.0.0.0
:: Internet kirish uchun TLS reverse proxy MAJBURIY (DEPLOY_WINDOWS.md, 7-bo'lim).
set BIND_HOST=%APP_BIND_HOST%
if "%BIND_HOST%"=="" (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="APP_BIND_HOST" set BIND_HOST=%%b
    )
)
if "%BIND_HOST%"=="" set BIND_HOST=127.0.0.1

:: Ichki chaqiriqlar (health check, frontend -> backend) uchun manzil:
:: 0.0.0.0 ga bog'langanda ham 127.0.0.1 orqali ishlaydi, aniq IP bo'lsa o'sha IP.
set INTERNAL_HOST=%BIND_HOST%
if "%INTERNAL_HOST%"=="0.0.0.0" set INTERNAL_HOST=127.0.0.1

:: ---------- Lokal IP (faqat LAN rejimda ko'rsatish uchun) ----------
set LOCAL_IP=127.0.0.1
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set TMP_IP=%%a
    set TMP_IP=!TMP_IP: =!
    if not "!TMP_IP!"=="127.0.0.1" set LOCAL_IP=!TMP_IP!
)
set DISPLAY_HOST=127.0.0.1
if not "%BIND_HOST%"=="127.0.0.1" set DISPLAY_HOST=!LOCAL_IP!

echo.
echo  UI  (Next.js)   : http://!DISPLAY_HOST!:%FRONTEND_PORT%
echo  API (FastAPI)   : http://!DISPLAY_HOST!:%BACKEND_PORT%
echo  Webhook         : http://!DISPLAY_HOST!:%BACKEND_PORT%/webhook/jira/{company_code}
echo  Bind host       : %BIND_HOST%
echo  Mode            : %WEBHOOK_EXECUTION_MODE%
if "%BIND_HOST%"=="127.0.0.1" (
    echo.
    echo  [i] Faqat shu kompyuterdan kirish mumkin. Tashqi kirish uchun
    echo      TLS reverse proxy sozlang ^(DEPLOY_WINDOWS.md, 7-bo'lim^).
)
echo.

:: ---------- Backend ----------
echo [API] Backend ishga tushirilmoqda...
start "QA-Backend :%BACKEND_PORT%" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m uvicorn services.webhook.jira_webhook_handler:app --host %BIND_HOST% --port %BACKEND_PORT%"

:: Backend tayyor bo'lishini kutish (health check)
where curl >nul 2>&1
if %errorlevel% neq 0 (
    echo [API] curl topilmadi - 10 sekund kutilyapti...
    timeout /t 10 /nobreak >nul
    goto BACKEND_DONE
)
set /a TRIES=0
:WAIT_BACKEND
curl -s -f -o nul http://%INTERNAL_HOST%:%BACKEND_PORT%/health 2>nul
if not errorlevel 1 goto BACKEND_OK
set /a TRIES+=1
if %TRIES% geq 60 goto BACKEND_FAIL
timeout /t 1 /nobreak >nul
goto WAIT_BACKEND
:BACKEND_FAIL
echo [XATO] Backend 60 sekundda ko'tarilmadi! "QA-Backend" oynasidagi xatoni tekshiring.
pause
exit /b 1
:BACKEND_OK
echo [OK] Backend tayyor
:BACKEND_DONE

:: ---------- Worker (faqat queue rejimida) ----------
if "%START_WORKER%"=="1" (
    echo [WORKER] Background worker ishga tushirilmoqda...
    start "QA-Worker" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m services.worker.main"
)

:: ---------- Frontend (production, standalone) ----------
echo [WEB] Next.js ishga tushirilmoqda...
set PORT=%FRONTEND_PORT%
set HOSTNAME=%BIND_HOST%
set BACKEND_API_BASE_URL=http://%INTERNAL_HOST%:%BACKEND_PORT%
set NEXT_PUBLIC_BACKEND_API_BASE_URL=http://%INTERNAL_HOST%:%BACKEND_PORT%
start "QA-Frontend :%FRONTEND_PORT%" /D "%~dp0frontend\.next\standalone" cmd /k "node server.js"

echo.
echo ============================================================
echo   Hammasi ishga tushdi! Ochilgan oynalar:
echo     QA-Backend  - FastAPI  (port %BACKEND_PORT%)
if "%START_WORKER%"=="1" echo     QA-Worker   - Background worker
echo     QA-Frontend - Next.js  (port %FRONTEND_PORT%)
echo.
echo   Brauzer: http://!DISPLAY_HOST!:%FRONTEND_PORT%
echo   To'xtatish: stop.bat
echo ============================================================
echo.
pause
endlocal
