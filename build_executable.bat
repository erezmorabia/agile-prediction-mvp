@echo off
REM Agile Practice Prediction System - Build Executable for Windows
REM This script builds a standalone executable using PyInstaller

echo ==========================================
echo Agile Practice Prediction System
echo Building Executable for Windows
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

REM Check if PyInstaller is installed
echo Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller^>=5.0.0
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        echo Please run: pip install pyinstaller^>=5.0.0
        pause
        exit /b 1
    )
    echo PyInstaller installed successfully
) else (
    echo PyInstaller is already installed
)
echo.

REM Check if spec file exists
if not exist "build_executable.spec" (
    echo ERROR: build_executable.spec not found
    echo Please ensure build_executable.spec exists in the project root
    pause
    exit /b 1
)

REM Clean previous builds
if exist "build" (
    echo Cleaning previous build directory...
    rmdir /s /q build
)

if exist "dist" (
    echo Cleaning previous dist directory...
    rmdir /s /q dist
)

echo Building executable...
echo This may take a few minutes...
echo.

REM Run PyInstaller
python -m PyInstaller build_executable.spec --clean

if errorlevel 1 (
    echo.
    echo ERROR: Build failed
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Build completed successfully!
echo ==========================================
echo.
echo Executable location: dist\AgilePredictionSystem.exe
echo.
echo To run the executable:
echo   dist\AgilePredictionSystem.exe
echo.
echo The executable will:
echo   1. Start the web server
echo   2. Automatically open your browser to http://localhost:8000
echo   3. Show server logs in the console
echo.
echo Press Ctrl+C to stop the server
echo.
pause

