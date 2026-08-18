# Agile Practice Recommendation MVP

An exploratory recommendation system that identifies likely next agile practices from an organization's recorded maturity history. It combines comparable-team evidence, observed practice transitions, and time-aware improvement popularity.

## Run the web app

Python 3.8+ is required.

```bash
git clone https://github.com/erezmorabia/agile-prediction-mvp.git
cd agile-prediction-mvp
./start_mac_linux.sh
```

On Windows:

```cmd
start_windows.bat
```

The startup scripts use `data/raw/combined_dataset.xlsx` when available, otherwise `data/raw/20250204_Cleaned_Dataset.xlsx`, install runtime dependencies when FastAPI is missing, and start the application at <http://localhost:8000>. The web server also opens the browser when it can.

For manual setup and troubleshooting, see [Installation](docs/INSTALLATION.md). For a short product walkthrough, see [Quick Start](docs/QUICK_START.md).

## What it does

For an eligible team and prediction month, the system:

1. Uses the team's latest snapshot strictly before that month as its baseline.
2. Scores practices that have not reached maturity level 3 using three evidence sources:
   - comparable teams' improvements in their next two recorded snapshots;
   - transitions after the target team's improvements in its two preceding snapshots; and
   - organization-wide historical and immediately recent improvement counts.
3. Selects one policy for the whole prediction month, then returns the two highest-ranked eligible practices. It returns an explanatory empty result when fewer than two practices are eligible.

The policy is not configured by the user. Each month it selects from 675 candidate combinations of peer count, similarity threshold, three factor weights, and popularity recency weight. Selection uses only earlier prediction months with complete three-snapshot outcomes. When none exist, the system uses a 100%-popularity bootstrap policy with equal historical/recent popularity weighting.

The full algorithm and API contract are documented in [Project Documentation](docs/PROJECT_DOCUMENTATION.md). The implementation flowcharts are in [docs/flowcharts](docs/flowcharts), and the request flows are in [docs/sequence-diagrams](docs/sequence-diagrams).

## Historical backtest

The backtest replays the policy that would have been available at each historical prediction month. It scores a case as a hit when either of the two recommendations appears among practices that improved between the baseline and its next three recorded snapshots. The cohort is fixed before any policy is scored: a case needs a usable baseline, at least two eligible practices, and at least one observed improvement in its outcome window.

On the checked-in dataset, the primary aggregate covers five prediction months with complete outcome windows (121 cases):

| Measure | Result |
| --- | ---: |
| Blend Hit Rate@2 | 58.0% |
| Random baseline | 26.0% |
| Improvement factor | 2.2x |
| Time-aware popularity arm | 55.7% |
| Blend minus popularity | +2.3 percentage points |

The remaining two prediction months are reported separately as sensitivity results because their three-snapshot outcome windows are truncated. These are historical, aggregate, exploratory results—not a guarantee for an individual team or evidence of proven superiority to popularity alone.

## Data and interfaces

The checked-in input dataset has 87 teams, 35 practices, 10 recorded months, and 655 team-month rows. Scores are integer maturity levels from 0 through 3; the processor normalizes them to 0 through 1. Team coverage varies by month, so a recommendation only requires that the team has a baseline before a valid global prediction month.

The application provides:

- a web interface with Statistics, Backtest, Sequences, and Recommendations tabs;
- a FastAPI API, including `POST /api/recommendations`, `POST /api/backtest`, `GET /api/stats`, and `GET /api/sequences`;
- an interactive CLI: `python src/main.py data/raw/combined_dataset.xlsx`.

The recommendations request accepts `team`, `month`, and optional `top_n`, which is constrained to `2`. Peer count and all scoring parameters are selected by the monthly policy, not passed by callers.

## Development

```bash
pip install -r requirements-dev.txt
make test
make check-all
```

`make test` excludes browser tests. Run `make test-ui` only with a live local server and the browser-test dependencies installed.

Repository-oriented implementation guidance is in [CLAUDE.md](CLAUDE.md).
