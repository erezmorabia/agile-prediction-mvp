#!/bin/bash

# Agile Practice Prediction System — Web Startup Script (macOS/Linux)

echo "Agile Practice Prediction System"
echo "---------------------------------"

# Resolve Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found. Install Python 3.8+ and try again."
    exit 1
fi

# Resolve data file
DATA_FILE="data/raw/combined_dataset.xlsx"
if [ ! -f "$DATA_FILE" ]; then
    DATA_FILE="data/raw/20250204_Cleaned_Dataset.xlsx"
    if [ ! -f "$DATA_FILE" ]; then
        echo "ERROR: No data file found in data/raw/"
        exit 1
    fi
fi

# Install dependencies automatically if needed
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies (first run only)..."
    $PYTHON_CMD -m pip install -r requirements.txt --quiet
fi

# Free port 8000 if something is already using it
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo "Starting server → http://localhost:8000"
echo "Press CTRL+C to stop."
echo ""

$PYTHON_CMD src/web_main.py "$DATA_FILE"

