# Quick Start Guide

**For Teachers/Evaluators - Get the system running in 3 steps!**

## Quick Start (3 Steps)

### Step 1: Install Dependencies

Open a terminal/command prompt in the project directory and run:

```bash
pip install -r requirements.txt
```

**Note:** If you're using Python 3, use `pip3` instead of `pip` on some systems.

### Step 2: Start the Web Interface

**Option A: Using the provided script (Easiest)**

**On macOS/Linux:**
```bash
chmod +x run_web.sh
./run_web.sh
```

**On Windows:**
```cmd
run_web.bat
```

**Option B: Manual start**
```bash
python src/web_main.py data/raw/combined_dataset.xlsx
```

**Option C: Standalone Executable (No Python installation required)**

If you want to avoid installing Python and dependencies, you can build a standalone executable:

**On macOS:**
```bash
./build_executable.sh
./dist/AgilePredictionSystem
```

**On Windows:**
```cmd
build_executable.bat
dist\AgilePredictionSystem.exe
```

The executable will automatically start the server and open your browser. See the "Building Executables" section in README.md for more details.

### Step 3: Open in Browser

Once the server starts, you'll see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

Open your web browser and navigate to:
**http://localhost:8000**

## What You Should See

### Web Interface Features:

1. **Recommendations Tab**
   - Select a team from the dropdown
   - Select a month to predict
   - Click "Get Recommendations"
   - See top 2 recommended practices with explanations

2. **Backtest Validation Tab**
   - Run validation on historical data
   - See accuracy metrics and improvement factors
   - Find optimal configuration parameters

3. **Statistics Tab**
   - View system statistics
   - See practice definitions and maturity levels
   - Explore improvement sequences

4. **Sequences Tab**
   - View learned improvement sequences
   - See transition probabilities between practices

## Alternative: Command Line Interface

If you prefer command-line interaction:

```bash
python src/main.py data/raw/combined_dataset.xlsx
```

Follow the interactive menu to:
- Get recommendations for a team
- Run backtest validation
- View statistics

## Expected Output

When the web server starts successfully, you should see:

```
Starting Agile Practice Prediction System (Web Interface)...
   Loading: data/raw/combined_dataset.xlsx

[1/5] Loading data...
[2/5] Validating data...
[3/5] Processing data...
[4/5] Initializing ML components...
[5/5] Starting web server...

INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## Stopping the Server

Press `CTRL+C` in the terminal to stop the web server.

## Testing the System

### Quick Test:
1. Go to the **Recommendations** tab
2. Select any team (e.g., "AADS")
3. Select a month (e.g., "2020-05-03")
4. Click "Get Recommendations"
5. You should see 2 recommended practices with scores and explanations

### Validation Test:
1. Go to the **Backtest Validation** tab
2. Click "Run Backtest Validation"
3. Wait for results (may take 1-2 minutes)
4. You should see accuracy metrics and improvement factors

## Troubleshooting

**Server won't start?**
- Check that port 8000 is not in use
- Verify data file exists: `ls data/raw/combined_dataset.xlsx`
- Make sure all dependencies are installed: `pip list`

**Can't access http://localhost:8000?**
- Make sure the server started successfully
- Check firewall settings
- Try http://127.0.0.1:8000 instead

**Import errors?**
- Activate virtual environment if using one
- Reinstall dependencies: `pip install -r requirements.txt`

## More Information

- **Full Documentation:** See `README.md`
- **Installation Details:** See `INSTALLATION.md`
- **Project Structure:** See `README.md` section "Project Structure"

## For Evaluation

The system demonstrates:
- **Machine Learning:** Collaborative filtering + sequence learning
- **Web Development:** FastAPI backend + modern frontend
- **Data Processing:** Excel data loading and validation
- **Validation:** Backtest methodology with accuracy metrics
- **Optimization:** Parameter tuning and search space optimization

**Key Metrics to Review:**
- Recommendation accuracy: ~68% (23x better than random baseline)
- Improvement factor: ~1.9x
- System handles 87 teams × 35 practices × 10 months of data

