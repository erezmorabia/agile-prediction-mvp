@echo off
REM Agile Practice Prediction System — Web Startup Script (Windows)

echo Agile Practice Prediction System
echo ---------------------------------

REM Check if a system Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and try again.
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    pause
    exit /b 1
)

REM Create and consistently use an isolated project environment
set VENV_PYTHON=.venv\Scripts\python.exe
if not exist "%VENV_PYTHON%" (
    echo Creating project environment ^(.venv^)...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create .venv. Ensure the Python venv module is installed.
        pause
        exit /b 1
    )
)

"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: .venv uses an unsupported Python version. Remove .venv and run this script again.
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

REM Reconcile all declared dependencies, including partially configured environments
echo Checking dependencies...
"%VENV_PYTHON%" -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Dependency installation failed. Check the messages above and your internet connection.
    pause
    exit /b 1
)

if not defined PORT set PORT=8000

echo Starting server ^> http://localhost:%PORT%
echo Press CTRL+C to stop.
echo.

"%VENV_PYTHON%" src\web_main.py "%DATA_FILE%"

pause
