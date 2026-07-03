@echo off
setlocal
title QA-Assistant - Stop

set BACKEND_PORT=8000
set FRONTEND_PORT=3000

echo.
echo QA-Assistant to'xtatilmoqda...
echo.

:: Oyna sarlavhasi bo'yicha (start.bat ochgan oynalar)
taskkill /F /T /FI "WINDOWTITLE eq QA-Backend*" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq QA-Worker*" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq QA-Frontend*" >nul 2>&1

:: Port bo'yicha zaxira usul (oyna topilmasa)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /C:":%BACKEND_PORT% " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /C:":%FRONTEND_PORT% " ^| findstr LISTENING') do taskkill /F /PID %%p >nul 2>&1

echo [OK] To'xtatildi.
echo.
pause
endlocal
