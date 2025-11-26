@echo off
REM Agile Practice Prediction System - Web Interface Startup Script
REM For Windows

echo ==========================================
echo Agile Practice Prediction System
echo Web Interface Startup
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo Using Python:
python --version
echo.

REM Check if data file exists
set DATA_FILE=data\raw\combined_dataset.xlsx
if not exist "%DATA_FILE%" (
    echo Warning: %DATA_FILE% not found
    set DATA_FILE=data\raw\20250204_Cleaned_Dataset.xlsx
    if not exist "%DATA_FILE%" (
        echo ERROR: No data file found in data\raw\
        echo Please ensure a data file exists
        pause
        exit /b 1
    )
    echo Using alternative data file: %DATA_FILE%
)

echo Data file: %DATA_FILE%
echo.

REM Check if required packages are installed
echo Checking dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Required packages not installed
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Dependencies OK
echo.

REM Start the web server
echo Starting web server...
echo Server will be available at: http://localhost:8000
echo Press CTRL+C to stop the server
echo.

python src\web_main.py "%DATA_FILE%"

pause

