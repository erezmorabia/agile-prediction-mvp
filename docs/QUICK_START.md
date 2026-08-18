# Quick Start

> **Requirement:** Python 3.8+ installed. That's it.

## Clone and run

**macOS / Linux:**
```bash
git clone https://github.com/erezmorabia/agile-prediction-mvp.git
cd agile-prediction-mvp
./start_mac_linux.sh
```

**Windows:**
```cmd
git clone https://github.com/erezmorabia/agile-prediction-mvp.git
cd agile-prediction-mvp
start_windows.bat
```

The script installs all dependencies automatically on first run, starts the server, and opens your browser to **http://localhost:8000**.

Press `CTRL+C` to stop.

---

## What to explore

| Tab | What it does |
|-----|-------------|
| **Recommendations** | Select a team and a displayed current-month → prediction-month pair → get likely next practices with explanations |
| **Backtest** | Replay the historical policy and view primary and sensitivity metrics (58.0% primary Hit Rate@2; exploratory, not a per-team guarantee) |
| **Statistics** | Dataset overview: 87 teams, 35 practices, 10 months |
| **Sequences** | Learned practice transition patterns between consecutive improvement-bearing steps |

**Suggested walkthrough:**
1. **Statistics** — understand the dataset
2. **Sequences** — see learned improvement patterns
3. **Recommendations** — pick any team (e.g. "AADS") and any month, click "Get Recommendations"
4. **Backtest** → click "Run Backtest Validation" to see the selected monthly policies and aggregate metrics. The first run can take up to a couple of minutes; later runs reuse cached evidence.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8000 in use | Close other apps on that port |
| Browser didn't open automatically | Navigate manually to http://localhost:8000 |
| `pip` errors during install | Run `pip install -r requirements.txt` manually, then re-run the script |
| Data file not found | Ensure `data/raw/combined_dataset.xlsx` exists in the project folder |
