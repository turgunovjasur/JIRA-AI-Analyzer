@echo off
title QA-Assistant - Setup

echo.
echo ============================================================
echo   QA-Assistant - Windows Setup
echo ============================================================
echo.

:: Python tekshirish
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATO] Python topilmadi!
    echo Python 3.11+ ni o'rnating: https://www.python.org/downloads/
    echo O'rnatishda "Add Python to PATH" ni belgilang!
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% topildi

:: Virtual environment
if exist ".venv\Scripts\python.exe" (
    echo [OK] Virtual environment mavjud
) else (
    echo [>>] Virtual environment yaratilmoqda...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [XATO] Virtual environment yaratishda xato!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment yaratildi
)

:: pip yangilash
echo [>>] pip yangilanmoqda...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet

:: Paketlar o'rnatish
echo.
echo [>>] Paketlar o'rnatilmoqda (10-20 daqiqa ketishi mumkin)...
echo     Iltimos kuting...
echo.
.venv\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [XATO] Paketlar o'rnatishda xato!
    pause
    exit /b 1
)

:: google-genai yangi SDK
.venv\Scripts\pip.exe install google-genai --quiet
echo [OK] google-genai SDK o'rnatildi

:: Data papkalari
echo [>>] Papkalar yaratilmoqda...
if not exist "data" mkdir data
if not exist "data\excel_reports" mkdir data\excel_reports
if not exist "data\vector_db" mkdir data\vector_db
if not exist "models" mkdir models
echo [OK] Papkalar tayyor

:: .env fayl
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [!!] .env.example dan .env yaratildi - uni to'ldiring!
    ) else (
        echo [!!] .env fayl topilmadi - uni yarating!
    )
) else (
    echo [OK] .env fayl mavjud
)

echo.
echo ============================================================
echo   Setup tayyor! Endi start.bat ni ishga tushiring.
echo ============================================================
echo.
pause
