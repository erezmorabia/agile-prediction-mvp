#!/bin/bash

# Agile Practice Prediction System - Web Interface Startup Script
# For macOS and Linux

echo "=========================================="
echo "Agile Practice Prediction System"
echo "Web Interface Startup"
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

# Check if data file exists
DATA_FILE="data/raw/combined_dataset.xlsx"
if [ ! -f "$DATA_FILE" ]; then
    echo "Warning: $DATA_FILE not found"
    DATA_FILE="data/raw/20250204_Cleaned_Dataset.xlsx"
    if [ ! -f "$DATA_FILE" ]; then
        echo "ERROR: No data file found in data/raw/"
        echo "Please ensure a data file exists"
        exit 1
    fi
    echo "Using alternative data file: $DATA_FILE"
fi

echo "Data file: $DATA_FILE"
echo ""

# Check if required packages are installed
echo "Checking dependencies..."
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo "ERROR: Required packages not installed"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

echo "Dependencies OK"
echo ""

# Start the web server
echo "Starting web server..."
echo "Server will be available at: http://localhost:8000"
echo "Press CTRL+C to stop the server"
echo ""

$PYTHON_CMD src/web_main.py "$DATA_FILE"

