# Installation Guide

This guide will help you set up the Agile Practice Prediction System on your computer.

## Prerequisites

### Python Version
- **Python 3.8 or higher** is required
- Check your Python version: `python --version` or `python3 --version`

### Operating System
- Windows, macOS, or Linux
- All platforms are supported

## Step-by-Step Installation

### Step 1: Clone or Extract the Project

If you received this as a ZIP file:
1. Extract the ZIP file to a location of your choice
2. Open a terminal/command prompt
3. Navigate to the project directory:
   ```bash
   cd agile-prediction-mvp
   ```

### Step 2: Create a Virtual Environment (Recommended)

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

Install all required Python packages:
```bash
pip install -r requirements.txt
```

This will install:
- pandas (data processing)
- numpy (numerical operations)
- scikit-learn (machine learning)
- scipy (scientific computing)
- openpyxl (Excel file reading)
- fastapi (web framework)
- uvicorn (web server)
- pydantic (data validation)

### Step 4: Verify Data Files

Ensure the data file exists:
```bash
# Check if the main data file exists
ls data/raw/combined_dataset.xlsx
```

On Windows:
```cmd
dir data\raw\combined_dataset.xlsx
```

If the file doesn't exist, check for alternative files:
- `data/raw/20250204_Cleaned_Dataset.xlsx`

### Step 5: Verify Installation

Test that everything is installed correctly:
```bash
python -c "import pandas, numpy, sklearn, fastapi; print('All dependencies installed successfully!')"
```

## Troubleshooting

### Issue: "python: command not found"
**Solution:** Use `python3` instead of `python` on macOS/Linux

### Issue: "pip: command not found"
**Solution:** Install pip or use `python -m pip` instead

### Issue: "Permission denied" errors
**Solution:** Use `pip install --user -r requirements.txt` or run with administrator/sudo privileges

### Issue: "No module named 'openpyxl'"
**Solution:** Make sure you activated your virtual environment and ran `pip install -r requirements.txt`

### Issue: Data file not found
**Solution:** 
1. Check that you're running commands from the project root directory
2. Verify the file exists: `ls data/raw/` (or `dir data\raw\` on Windows)
3. Use the full path to the file when running: `python src/web_main.py /full/path/to/data/raw/combined_dataset.xlsx`

### Issue: Port 8000 already in use
**Solution:** 
- Close any other applications using port 8000
- Or modify `src/web_main.py` to use a different port (change `uvicorn.run(..., port=8000)` to another port)

## Next Steps

Once installation is complete, see **QUICK_START.md** for instructions on running the application.

## System Requirements

- **RAM:** Minimum 2GB (4GB recommended)
- **Disk Space:** ~500MB for project + dependencies
- **Internet:** Required only for initial dependency installation

## Support

If you encounter any issues not covered here, please check:
1. Python version compatibility (3.8+)
2. All dependencies are installed correctly
3. You're running commands from the project root directory
4. Data files are present in `data/raw/` directory

