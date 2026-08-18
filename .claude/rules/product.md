# Product

## Domain Story

The system analyzes improvement histories from 87 engineering teams tracked across 10 months. For any team at any given month, it asks: *"Which teams were in a similar position, what did they improve next, what practice transitions typically follow, and what is the organization improving right now?"* It blends all three signals into exactly two ranked recommendations, using one policy selected per prediction month from prior completed outcomes - never tuned on the month being predicted or on the team's own future. A backtest of this walk-forward policy shows a higher primary aggregate than a properly time-aware popularity comparison arm on the same evaluable cases (see `tests/test_blend_reproduction.py` for the pinned figures and caveats; this remains exploratory, not a claim of proven superiority over popularity alone).

## Core Domain Concepts

| Concept | Definition |
|---|---|
| **Team** | An engineering/delivery team tracked over time; identified by name string |
| **Practice** | An agile capability (e.g., CI/CD, Test Automation); each team has a score per practice per month |
| **Maturity Level** | Practice score: 0 = not implemented, 1 = basic, 2 = intermediate, 3 = mature |
| **Month** | A numeric snapshot timestamp in the project's YYMMDD-style encoding (for example, `200101`); the fundamental time unit |
| **Improvement** | A practice score increase from one month to the next (any positive delta) |
| **Recommendation** | A predicted practice to improve next, with a confidence score 0–1; the primary flow always returns exactly two |
| **Similarity Score** | Cosine similarity between two practice maturity vectors; range 0–1 |
| **Sequence** | An empirical transition: a practice improved in one improvement-bearing step and another improved in the next such step |
| **Popularity** | Organization-wide practice-improvement frequency; time-aware popularity blends all-time counts with the single most recent transition |
| **Policy** | One combination of peer count, similarity threshold, similarity/sequence/popularity weights, and popularity recency weight; selected once per prediction month, not per team |
| **Bootstrap Policy** | The fallback policy (100% popularity, 50/50 recency) used when no prior prediction month yet has a completed 3-snapshot outcome window |
| **Recommendable team-month** | Has a usable baseline snapshot and ≥2 candidate practices below max maturity; no outcome required - used by the live flow |
| **Evaluable team-month** | Recommendable, and at least one practice improved in the 3-snapshot outcome window; used by the backtest cohort and by monthly policy selection |
| **Backtest** | Rolling window validation: for each prediction month, select that month's policy from prior completed outcomes, predict, check against actual improvements |
| **Random Baseline** | Probability of at least one correct recommendation by random selection; comparison benchmark |
| **Time-Aware Popularity Arm** | The backtest's independent comparison policy: pure popularity (0% similarity, 0% sequence), selected under the same monthly walk-forward rule |
| **Practice Profile** | A team's practices grouped into 4 maturity levels at a given month |

## Use Cases

| ID | Use Case | Actor | Trigger | Domains |
|---|---|---|---|---|
| UC-01 | Get Recommendations | Analyst | Selects team + month, clicks "Get Recommendations" | ml, api, frontend |
| UC-02 | Run Backtest Validation | Analyst | Clicks "Run Backtest" on Backtest tab | validation, api, frontend |
| UC-04 | Explore Improvement Sequences | Analyst | Navigates to Sequences tab | ml, api, frontend |
| UC-05 | View System Statistics | Analyst | Navigates to Statistics tab | data, api, frontend |

For detailed use case flows, see `/uc-01-get-recommendations`, `/uc-02-run-backtest-validation`, `/uc-04-explore-improvement-sequences`, `/uc-05-view-system-statistics`.

There is no static all-history parameter optimizer (UC-03 was removed - the monthly-selected policy, `/domain-ml`, is the only configuration authority for the primary flow and its backtest).

## User Journey Summaries

- **Core analysis:** UC-05 (understand data shape) → UC-04 (see existing sequences) → UC-01 (get recommendations for a team)
- **Model validation:** UC-02 (validate the current monthly-policy blend against a time-aware popularity comparison, split into primary and sensitivity results)

## Domain Validation Rules

- **Minimum history:** A team needs a usable baseline snapshot (some observed month strictly before the prediction month) before recommendations can be generated
- **Prediction start month:** Only months at global index 3+ are valid prediction months; months at index 0–2 are reserved as minimum training history
- **Backtest minimum:** Rolling window requires ≥ 4 months of data
- **Fixed component windows:** Similarity look-ahead and sequence recency are both fixed at 2 observed snapshots - never tunable, never vary by team or month
- **Global monthly policy selection:** Peer count (5/10/19), minimum similarity (0.0/0.5/0.75), similarity/sequence/popularity weights (15 combinations of 0/25/50/75/100%), and popularity recency (0/25/50/75/100%) are chosen once per prediction month - 675 candidate policies - by maximizing mean HR@2 over strictly earlier prediction months whose full 3-snapshot outcome window has already closed. Never selected per team, never using the target month's own outcome
- **Bootstrap policy:** Used when no prior prediction month has a completed outcome window yet (100% popularity, 50/50 recency); peer count and similarity threshold are reported as not applicable, never as a default value
- **Practice exclusion at startup:** Practices with > 90% missing values are dropped before model building
- **Maxed-out practices excluded:** Practices with normalized score ≥ 1.0 are never recommended
- **Validation/outcome window:** Checks improvements in a 3-snapshot window (baseline's prediction month, the next observed snapshot, and the one after that) to account for adoption timelines
- **Evaluable cohort fixed before scoring:** A team-month's evaluable status never depends on which policy is being scored, and is identical across all 675 candidate policies and both reported comparison arms
- **Primary vs sensitivity:** Backtest aggregates split into primary (prediction months with a complete 3-snapshot outcome window against the dataset's end) and sensitivity (all prediction months) - never mixed together
- **Backtest cancellation:** `_cancelled` flag on `BacktestEngine` is polled every 10 cases and at each month boundary; a fresh `run_backtest()` call always resets it first so a stale prior cancellation can't silently cancel a new run
