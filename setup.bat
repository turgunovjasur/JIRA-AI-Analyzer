@echo off
setlocal
cd /d "%~dp0"
title QA-Assistant - Setup

echo.
echo ============================================================
echo   QA-Assistant - Windows Setup
echo ============================================================
echo.

:: ---------- 1) Python ----------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATO] Python topilmadi!
    echo        Python 3.11+ o'rnating: https://www.python.org/downloads/
    echo        O'rnatishda "Add Python to PATH" ni ALBATTA belgilang!
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% topildi

:: ---------- 2) Node.js ----------
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATO] Node.js topilmadi!
    echo        Node.js 20+ LTS o'rnating: https://nodejs.org/
    pause
    exit /b 1
)
for /f %%v in ('node --version') do set NODE_VER=%%v
echo [OK] Node.js %NODE_VER% topildi

:: ---------- 3) Virtual environment ----------
if exist ".venv\Scripts\python.exe" (
    echo [OK] Virtual environment mavjud
) else (
    echo [..] Virtual environment yaratilmoqda...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [XATO] Virtual environment yaratishda xato!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment yaratildi
)

:: ---------- 4) Python paketlar ----------
echo [..] pip yangilanmoqda...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo.
echo [..] Python paketlar o'rnatilmoqda (bir necha daqiqa)...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [XATO] Python paketlar o'rnatishda xato!
    pause
    exit /b 1
)
echo [OK] Python paketlar tayyor

:: ---------- 5) Frontend (Next.js) ----------
echo.
echo [..] Frontend paketlar o'rnatilmoqda...
cd frontend
call npm ci
if %errorlevel% neq 0 (
    echo [XATO] npm ci muvaffaqiyatsiz! Internet/proxy ni tekshiring.
    cd ..
    pause
    exit /b 1
)

echo [..] Frontend production build qilinmoqda (bir necha daqiqa)...
call npm run build
if %errorlevel% neq 0 (
    echo [XATO] Frontend build muvaffaqiyatsiz!
    cd ..
    pause
    exit /b 1
)
cd ..

:: standalone server uchun static fayllarni nusxalash
if exist "frontend\.next\standalone\server.js" (
    xcopy /E /I /Y "frontend\.next\static" "frontend\.next\standalone\.next\static" >nul
    if exist "frontend\public" xcopy /E /I /Y "frontend\public" "frontend\.next\standalone\public" >nul
    echo [OK] Frontend build tayyor
) else (
    echo [XATO] frontend\.next\standalone\server.js topilmadi - build xato!
    pause
    exit /b 1
)

:: ---------- 6) Papkalar ----------
if not exist "data" mkdir data
if not exist "data\excel_reports" mkdir data\excel_reports
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups
echo [OK] Papkalar tayyor

:: ---------- 7) .env ----------
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo.
        echo [!!] .env.example dan .env yaratildi.
        echo [!!] .env faylini OCHIB, barcha CHANGE_THIS_* qiymatlarni
        echo [!!] va API kalitlarni to'ldiring! ^(DEPLOY_WINDOWS.md ga qarang^)
        echo [!!] APP_WEBHOOK_EXECUTION_MODE=queue - worker jarayoni MAJBURIY
        echo [!!] ^(start.bat uni avtomatik ishga tushiradi^). 'inline' rejim
        echo [!!] crash-recovery'ni o'chiradi - faqat dev uchun.
    ) else (
        echo [!!] .env.example topilmadi - .env faylini qo'lda yarating!
    )
) else (
    echo [OK] .env fayl mavjud
)

echo.
echo ============================================================
echo   Setup tayyor!
echo   1^) .env faylini to'ldiring (agar hali qilmagan bo'lsangiz^)
echo   2^) PostgreSQL da baza yarating (DEPLOY_WINDOWS.md^)
echo   3^) start.bat ni ishga tushiring
echo.
echo   ESLATMA: queue rejimida background worker MAJBURIY -
echo   start.bat uni avtomatik ishga tushiradi (QA-Worker oynasi^).
echo ============================================================
echo.
pause
