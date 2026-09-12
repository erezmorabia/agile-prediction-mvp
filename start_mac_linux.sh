#!/bin/bash

# Agile Practice Prediction System — Web Startup Script (macOS/Linux)

echo "Agile Practice Prediction System"
echo "---------------------------------"

# Resolve the system Python used to create the project environment
if command -v python3 &> /dev/null; then
    SYSTEM_PYTHON="python3"
elif command -v python &> /dev/null; then
    SYSTEM_PYTHON="python"
else
    echo "ERROR: Python not found. Install Python 3.10+ and try again."
    exit 1
fi

if ! "$SYSTEM_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    echo "ERROR: Python 3.10 or newer is required."
    exit 1
fi

# Create and consistently use an isolated project environment
VENV_PYTHON=".venv/bin/python"
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creating project environment (.venv)..."
    if ! "$SYSTEM_PYTHON" -m venv .venv; then
        echo "ERROR: Could not create .venv. Ensure the Python venv module is installed."
        exit 1
    fi
fi

if ! "$VENV_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    echo "ERROR: .venv uses an unsupported Python version. Remove .venv and run this script again."
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

# Reconcile all declared dependencies, including partially configured environments
echo "Checking dependencies..."
if ! "$VENV_PYTHON" -m pip install -r requirements.txt --quiet; then
    echo "ERROR: Dependency installation failed. Check the messages above and your internet connection."
    exit 1
fi

PORT="${PORT:-8000}"
export PORT

echo "Starting server → http://localhost:$PORT"
echo "Press CTRL+C to stop."
echo ""

"$VENV_PYTHON" src/web_main.py "$DATA_FILE"
