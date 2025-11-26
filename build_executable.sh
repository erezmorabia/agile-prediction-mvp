#!/bin/bash

# Agile Practice Prediction System - Build Executable for macOS
# This script builds a standalone executable using PyInstaller

echo "=========================================="
echo "Agile Practice Prediction System"
echo "Building Executable for macOS"
echo "=========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "ERROR: Python is not installed or not in PATH"
        echo "Please install Python 3.8 or higher"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD --version
echo ""

# Check if PyInstaller is installed
echo "Checking PyInstaller..."
if ! $PYTHON_CMD -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    $PYTHON_CMD -m pip install pyinstaller>=5.0.0
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install PyInstaller"
        echo "Please run: pip install pyinstaller>=5.0.0"
        exit 1
    fi
    echo "PyInstaller installed successfully"
else
    echo "PyInstaller is already installed"
fi
echo ""

# Check if spec file exists
if [ ! -f "build_executable.spec" ]; then
    echo "ERROR: build_executable.spec not found"
    echo "Please ensure build_executable.spec exists in the project root"
    exit 1
fi

# Clean previous builds
if [ -d "build" ]; then
    echo "Cleaning previous build directory..."
    rm -rf build
fi

if [ -d "dist" ]; then
    echo "Cleaning previous dist directory..."
    rm -rf dist
fi

echo "Building executable..."
echo "This may take a few minutes..."
echo ""

# Run PyInstaller
$PYTHON_CMD -m PyInstaller build_executable.spec --clean

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Build completed successfully!"
    echo "=========================================="
    echo ""
    echo "Executable location: dist/AgilePredictionSystem"
    echo ""
    echo "To run the executable:"
    echo "  ./dist/AgilePredictionSystem"
    echo ""
    echo "The executable will:"
    echo "  1. Start the web server"
    echo "  2. Automatically open your browser to http://localhost:8000"
    echo "  3. Show server logs in the console"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
else
    echo ""
    echo "ERROR: Build failed"
    echo "Please check the error messages above"
    exit 1
fi

