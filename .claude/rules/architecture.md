# Architecture

## Service Overview

| Component | Role |
|---|---|
| `src/web_main.py` | Entry point; orchestrates data loading, ML init, FastAPI startup |
| `src/main.py` | CLI entry point (non-web usage) |
| `src/api/` | FastAPI app factory, route handlers, service layer, Pydantic models |
| `src/ml/` | ML engine: similarity search, sequence learning, hybrid recommendations |
| `src/data/` | Data loading, normalization, validation, practice definitions |
| `src/validation/` | Backtest validation, parameter optimization, accuracy metrics |
| `src/interface/` | CLI interface and output formatting |
| `web/` | Static SPA served by FastAPI at `/` |

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI + uvicorn |
| Data processing | pandas, numpy, openpyxl |
| ML algorithms | scikit-learn (`cosine_similarity`), scipy (`comb`) |
| Request/response | Pydantic v2 |
| Executable packaging | PyInstaller (`dist/` dir) |
| Code quality | mypy, pylint, ruff, pydocstyle |
| Tests | pytest, pytest-cov |

## Directory Structure

```
src/
├── web_main.py              # Web entry point (PyInstaller-aware)
├── main.py                  # CLI entry point
├── data/
│   ├── loader.py            # DataLoader: Excel → DataFrame
│   ├── processor.py         # DataProcessor: normalize 0-3→0-1, build team_histories
│   ├── validator.py         # DataValidator: quality checks, filter >90% missing
│   └── practice_definitions.py  # PracticeDefinitionsLoader: level descriptions
├── ml/
│   ├── similarity.py        # SimilarityEngine: cosine similarity, K-NN lookup
│   ├── sequences.py         # SequenceMapper: Markov transition matrix + cache
│   └── recommender.py       # RecommendationEngine: hybrid scoring (main engine)
├── validation/
│   ├── backtest.py          # BacktestEngine: rolling window validation
│   ├── optimizer.py         # OptimizationEngine: grid search + _cancelled flag
│   └── metrics.py           # Accuracy calculations, random baseline
├── api/
│   ├── main.py              # create_app(): FastAPI app factory
│   ├── routes.py            # create_routes(): all 10 API route handlers
│   ├── service.py           # APIService: bridges routes ↔ ML components
│   └── models.py            # Pydantic request/response models
└── interface/
    ├── cli.py               # Interactive CLI
    └── formatter.py         # Output formatting utilities
web/
├── index.html               # Single-page app shell (4 tabs)
└── static/
    ├── js/
    │   ├── app.js           # Tab init, event handlers, render functions
    │   └── api.js           # API client wrapper functions
    └── css/style.css
tests/                       # 13 pytest files
data/raw/                    # Excel data files (gitignored)
results/                     # Optimization output JSON files
```

## Functional Domains

| Domain | Purpose | Key Components | Key Functions |
|---|---|---|---|
| data | Load Excel, normalize scores, validate data, filter practices | `DataLoader`, `DataProcessor`, `DataValidator`, `PracticeDefinitionsLoader` | `load()`, `process()`, `validate()`, `filter_high_missing_practices()` |
| ml | Similarity search, sequence learning, hybrid recommendation scoring | `SimilarityEngine`, `SequenceMapper`, `RecommendationEngine` | `find_similar_teams()`, `learn_sequences_up_to_month()`, `recommend()`, `get_recommendation_explanation()` |
| validation | Rolling window backtest, grid search optimization, accuracy metrics | `BacktestEngine`, `OptimizationEngine` | `run_backtest()`, `find_optimal_config()`, `cancel()`, `generate_parameter_combinations()` |
| api | FastAPI routes, service orchestration, request/response models | `APIService`, route handlers, Pydantic models | `create_routes()`, `get_recommendations()`, `run_backtest()`, `find_optimal_config()`, `cancel_optimization()` |
| frontend | Single-page web app, 4-tab UI, API client | `index.html`, `app.js`, `api.js`, `style.css` | `initializeRecommendations()`, `initializeBacktest()`, `initializeStats()`, `initializeSequences()` |

For detailed domain information, see `/domain-data`, `/domain-ml`, `/domain-validation`, `/domain-api`, `/domain-frontend`.

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/teams` | List all teams with metadata |
| GET | `/api/teams/with-improvements` | Teams/months where improvements occurred |
| GET | `/api/teams/{team_name}/months` | Available prediction months for a team |
| POST | `/api/recommendations` | Generate practice recommendations |
| POST | `/api/backtest` | Run rolling window backtest |
| GET | `/api/stats` | System statistics |
| GET | `/api/sequences` | Learned improvement sequences |
| POST | `/api/optimize` | Run parameter grid search |
| POST | `/api/optimize/cancel` | Cancel in-progress optimization |
| GET | `/api/optimize/latest` | Latest saved optimization results |

## Startup Sequence

```
web_main.py
  → DataLoader.load()
  → DataValidator.validate() + filter_high_missing_practices(threshold=90%)
  → DataProcessor.process()
  → SimilarityEngine(processor)
  → SequenceMapper(processor, practices) → learn_sequences()
  → RecommendationEngine(similarity_engine, sequence_mapper, practices)
  → APIService(recommender, processor)
  → create_app(service) → uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Architectural Constraints

- **Temporal ordering (CRITICAL):** All ML algorithms must only access data from months ≤ current_month. Future data must never influence predictions. Enforced by `test_temporal_boundaries.py`.
- **Practice filtering at startup:** Practices with >90% missing values are excluded before model building; `practices` list updated in-place.
- **Thread pool for optimization:** `POST /api/optimize` runs in a `ThreadPoolExecutor(max_workers=1)` so the event loop stays free to process `/api/optimize/cancel`.
- **Cancellation pattern:** `OptimizationEngine._cancelled` flag is polled inside the backtest loop (every 10 teams and at each month boundary); set via `cancel()` → `POST /api/optimize/cancel`.
- **PyInstaller path resolution:** `get_resource_path()` in `web_main.py` checks `sys._MEIPASS` first (frozen) then project root (dev).
- **Run from project root:** All imports assume project root is in `sys.path`.

## Known Technical Debt

- Many pre-existing mypy type errors — scope type-check to new code only
- `SimilarityEngine.build_similarity_matrix()` exists but is unused by the main recommendation path (cross-temporal `find_similar_teams()` recomputes per call without using the cached matrix)
