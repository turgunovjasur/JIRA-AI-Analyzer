@echo off
setlocal
cd /d "%~dp0"
title QA-Assistant - DB Backup

:: pg_dump PATH da bo'lishi kerak (PostgreSQL bin papkasi).
:: Ulanish ma'lumotlari .env dagi APP_POSTGRES_DSN dan olinadi.

if not exist ".venv\Scripts\python.exe" (
    echo [XATO] Virtual environment topilmadi! Avval setup.bat ni ishga tushiring.
    pause
    exit /b 1
)

where pg_dump >nul 2>&1
if %errorlevel% neq 0 (
    echo [XATO] pg_dump topilmadi!
    echo        PostgreSQL bin papkasini PATH ga qo'shing, masalan:
    echo        C:\Program Files\PostgreSQL\16\bin
    pause
    exit /b 1
)

:: DSN ni parse qilish (bo'sh parol uchun '-' placeholder)
for /f "tokens=1-5" %%a in ('.venv\Scripts\python.exe -c "import os;from dotenv import load_dotenv;load_dotenv();from urllib.parse import urlsplit,unquote;u=urlsplit(os.getenv('APP_POSTGRES_DSN',''));print(u.username or 'postgres',unquote(u.password) if u.password else '-',u.hostname or 'localhost',u.port or 5432,(u.path or '/jira_ai_analyzer').lstrip('/'))"') do (
    set DB_USER=%%a
    set DB_PASS=%%b
    set DB_HOST=%%c
    set DB_PORT=%%d
    set DB_NAME=%%e
)
if "%DB_PASS%"=="-" (set PGPASSWORD=) else (set PGPASSWORD=%DB_PASS%)

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i
if not exist "backups" mkdir backups

set BACKUP_FILE=backups\%DB_NAME%_%TS%.dump
echo [..] Backup olinmoqda: %BACKUP_FILE%
pg_dump -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -F c -f "%BACKUP_FILE%"
if %errorlevel% neq 0 (
    echo [XATO] Backup muvaffaqiyatsiz!
    pause
    exit /b 1
)
echo [OK] Backup tayyor: %BACKUP_FILE%

:: 7 kundan eski backuplarni o'chirish
forfiles /P backups /M *.dump /D -7 /C "cmd /c del @path" 2>nul

echo.
pause
endlocal
