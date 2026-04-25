# Product

## Domain Story

The system analyzes improvement histories from 87 engineering teams tracked across 10 months. For any team at any given month, it asks: *"Which teams were in a similar position, what did they improve next, and what practice transitions typically follow?"* It combines both signals into ranked recommendations. Achieved 49% accuracy — 2.0× better than random selection — eliminating manual analysis and scaling to 70+ teams simultaneously.

## Core Domain Concepts

| Concept | Definition |
|---|---|
| **Team** | An engineering/delivery team tracked over time; identified by name string |
| **Practice** | An agile capability (e.g., CI/CD, Test Automation); each team has a score per practice per month |
| **Maturity Level** | Practice score: 0 = not implemented, 1 = basic, 2 = intermediate, 3 = mature |
| **Month** | A snapshot timestamp in yyyymmdd format; the fundamental time unit |
| **Improvement** | A practice score increase from one month to the next (any positive delta) |
| **Recommendation** | A predicted practice to improve next, with a confidence score 0–1 |
| **Similarity Score** | Cosine similarity between two practice maturity vectors; range 0–1 |
| **Sequence** | A Markov transition: "practice A improved → practice B typically follows" |
| **Backtest** | Rolling window validation: train on past months, predict, check against actual improvements |
| **Random Baseline** | Probability of at least one correct recommendation by random selection; comparison benchmark |
| **Practice Profile** | A team's practices grouped into 4 maturity levels at a given month |

## Use Cases

| ID | Use Case | Actor | Trigger | Domains |
|---|---|---|---|---|
| UC-01 | Get Recommendations | Analyst | Selects team + month, clicks "Get Recommendations" | ml, api, frontend |
| UC-02 | Run Backtest Validation | Analyst | Clicks "Run Backtest" on Backtest tab | validation, api, frontend |
| UC-03 | Run Parameter Optimization | Analyst | Configures param ranges, clicks "Find Optimal Config" | validation, api, frontend |
| UC-04 | Explore Improvement Sequences | Analyst | Navigates to Sequences tab | ml, api, frontend |
| UC-05 | View System Statistics | Analyst | Navigates to Statistics tab | data, api, frontend |

For detailed use case flows, see `/uc-01-get-recommendations`, `/uc-02-run-backtest-validation`, `/uc-03-run-parameter-optimization`, `/uc-04-explore-improvement-sequences`, `/uc-05-view-system-statistics`.

## User Journey Summaries

- **Core analysis:** UC-05 (understand data shape) → UC-04 (see existing sequences) → UC-01 (get recommendations for a team)
- **Model tuning:** UC-02 (validate current accuracy) → UC-03 (optimize parameters) → UC-02 (re-validate with new params)

## Domain Validation Rules

- **Minimum history:** A team needs ≥ 2 months of data before predictions can be generated
- **Prediction start month:** Only months 3+ (globally) are available for prediction; months 1–2 are reserved as training history
- **Backtest minimum:** Rolling window requires ≥ 4 months of data; starts from month index 3 (0-based)
- **Similarity threshold:** Default `min_similarity_threshold = 0.75`; teams below this are excluded from collaborative filtering
- **Practice exclusion at startup:** Practices with > 90% missing values are dropped before model building
- **Maxed-out practices excluded:** Practices with normalized score ≥ 1.0 are never recommended
- **Validation window:** Backtest checks improvements in a 3-month window (test_month, +1, +2) to account for adoption timelines
- **Teams with no improvements skipped:** In backtest, teams with zero improvements in the 3-month window are excluded from accuracy calculation (not a model failure)
- **Optimization cancellation:** `_cancelled` flag on `OptimizationEngine` is polled every 10 teams and at each month; returns partial results with `cancelled: True`
