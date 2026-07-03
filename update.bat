@echo off
setlocal
cd /d "%~dp0"
title QA-Assistant - Update

echo.
echo ============================================================
echo   QA-Assistant - Yangilash (git pull + build)
echo ============================================================
echo.
echo [!!] Yangilashdan avval stop.bat bilan to'xtatgan bo'lishingiz kerak.
echo      Davom etish uchun istalgan tugmani bosing...
pause >nul

:: ---------- 1) Git pull ----------
echo [..] GitHub dan yangi kod olinmoqda...
git pull origin main
if %errorlevel% neq 0 (
    echo [XATO] git pull muvaffaqiyatsiz! Internet yoki lokal o'zgarishlarni tekshiring.
    pause
    exit /b 1
)

:: ---------- 2) Python paketlar ----------
echo [..] Python paketlar yangilanmoqda...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [XATO] pip install muvaffaqiyatsiz!
    pause
    exit /b 1
)

:: ---------- 3) Frontend build ----------
echo [..] Frontend yangilanmoqda...
cd frontend
call npm ci
if %errorlevel% neq 0 (
    echo [XATO] npm ci muvaffaqiyatsiz!
    cd ..
    pause
    exit /b 1
)
call npm run build
if %errorlevel% neq 0 (
    echo [XATO] Frontend build muvaffaqiyatsiz!
    cd ..
    pause
    exit /b 1
)
cd ..
xcopy /E /I /Y "frontend\.next\static" "frontend\.next\standalone\.next\static" >nul
if exist "frontend\public" xcopy /E /I /Y "frontend\public" "frontend\.next\standalone\public" >nul

echo.
echo ============================================================
echo   Yangilash tayyor! Endi start.bat ni ishga tushiring.
echo   (DB migratsiyalar backend ishga tushganda avtomatik qo'llanadi)
echo ============================================================
echo.
pause
endlocal
