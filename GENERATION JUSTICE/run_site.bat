@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python and try again.
    pause
    exit /b 1
)

echo Installing required packages...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Package installation failed.
    pause
    exit /b 1
)

echo.
echo Starting Generation Justice...
set PORT=8000
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if not errorlevel 1 (
    set PORT=8001
)

echo Open this address in your browser:
echo http://127.0.0.1:%PORT%
echo.
echo Demo login:
echo demo@generationjustice.org
echo demo123
echo.

python -m uvicorn main:app --host 127.0.0.1 --port %PORT% --reload
pause
