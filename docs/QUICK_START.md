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
| **Recommendations** | Select a team + month → get top predicted practices with explanations |
| **Backtest** | Validate accuracy on historical data (~49%, 2.0× better than random) |
| **Statistics** | Dataset overview: 87 teams, 35 practices, 10 months |
| **Sequences** | Learned Markov transition patterns between practices |

**Suggested walkthrough:**
1. **Statistics** — understand the dataset
2. **Sequences** — see learned improvement patterns
3. **Recommendations** — pick any team (e.g. "AADS") and any month, click "Get Recommendations"
4. **Backtest** → click "Run Backtest Validation" to see live accuracy metrics (~1–2 min)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8000 in use | Close other apps on that port |
| Browser didn't open automatically | Navigate manually to http://localhost:8000 |
| `pip` errors during install | Run `pip install -r requirements.txt` manually, then re-run the script |
| Data file not found | Ensure `data/raw/combined_dataset.xlsx` exists in the project folder |
