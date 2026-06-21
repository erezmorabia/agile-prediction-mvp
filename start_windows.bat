@echo off
REM Agile Practice Prediction System — Web Startup Script (Windows)

echo Agile Practice Prediction System
echo ---------------------------------

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.8+ and try again.
    pause
    exit /b 1
)

REM Resolve data file
set DATA_FILE=data\raw\combined_dataset.xlsx
if not exist "%DATA_FILE%" (
    set DATA_FILE=data\raw\20250204_Cleaned_Dataset.xlsx
    if not exist "%DATA_FILE%" (
        echo ERROR: No data file found in data\raw\
        pause
        exit /b 1
    )
)

REM Install dependencies automatically if needed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies (first run only)...
    python -m pip install -r requirements.txt --quiet
)

REM Free port 8000 if something is already using it
FOR /F "tokens=5" %%a IN ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') DO taskkill /F /PID %%a >nul 2>&1

REM Open browser automatically after server starts
start /b cmd /c "timeout /t 4 >nul && start http://localhost:8000"

echo Starting server ^> http://localhost:8000
echo Press CTRL+C to stop.
echo.

python src\web_main.py "%DATA_FILE%"

pause

