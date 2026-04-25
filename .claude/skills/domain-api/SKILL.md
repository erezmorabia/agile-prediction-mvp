---
name: domain-api
description: FastAPI app factory, route handlers, APIService orchestration, Pydantic models, startup. Use when modifying endpoints, request/response shapes, service layer logic, or startup initialization.
---

# Domain: API

## Summary
`APIService` wraps all ML and validation components for HTTP consumption. `create_routes()` registers 10 endpoints on a shared `APIRouter`; `create_app()` mounts static files and wires routes. Optimization runs in a `ThreadPoolExecutor` so the event loop stays free for cancel requests.

## Data Flows

- **App startup:** `create_app(service)` → mounts `web/static` at `/static` → serves `web/index.html` at `/` → calls `create_routes(service)` and includes the router
- **Request lifecycle:** HTTP request → route handler (async) → `APIService` method → ML/validation component → Pydantic model → JSON response
- **Optimization async pattern:** `POST /api/optimize` calls `loop.run_in_executor(_executor, lambda: service.find_optimal_config(...))` with `ThreadPoolExecutor(max_workers=1)` — allows concurrent `POST /api/optimize/cancel` to be processed by the same event loop
- **Practice definitions:** `APIService.__init__()` tries `data/raw/practice_level_definitions.xlsx` then falls back to legacy filename; included in `GET /api/stats` response if loaded
- **Missing values:** `web_main.py` sets `service.missing_values_details` after startup; surfaced via `GET /api/stats`

## External API Patterns

- All endpoints under `/api/` prefix; static files at `/static/`; SPA shell at `/`
- Optimization endpoint uses `asyncio.get_event_loop().run_in_executor()` — do not convert to `await asyncio.to_thread()` without testing cancel concurrency

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `create_app()` | `src/api/main.py` | `web_main.py` | `service: APIService` → `FastAPI` app instance |
| `create_routes()` | `src/api/routes.py:31` | `create_app()` | `service: APIService` → `APIRouter` with all 10 routes registered |
| `APIService.get_all_teams()` | `src/api/service.py:51` | `GET /api/teams` | → `list[dict]` sorted by num_months desc |
| `APIService.get_teams_with_improvements()` | `src/api/service.py:80` | `GET /api/teams/with-improvements` | → `list[dict]` (team, month, improvements) |
| `APIService.get_team_months()` | `src/api/service.py:133` | `GET /api/teams/{team_name}/months` | `team_name` → `list[int]` (month 3+ only) or `None` |
| `APIService.get_recommendations()` | `src/api/service.py:172` | `POST /api/recommendations` | `team_name, month, top_n, k_similar` → dict with `recommendations`, `validation`, `practice_profile` |
| `APIService.run_backtest()` | `src/api/service.py:430` | `POST /api/backtest` | `train_ratio, config` → backtest results dict |
| `APIService.find_optimal_config()` | `src/api/service.py:507` | `POST /api/optimize` (via executor) | param range lists → optimization results dict |
| `APIService.cancel_optimization()` | `src/api/service.py:550` | `POST /api/optimize/cancel` | → sets `optimizer_engine._cancelled = True` |
| `APIService.get_system_stats()` | `src/api/service.py:556` | `GET /api/stats` | → dict with team/practice/month counts, similarity stats, definitions, missing values |
| `APIService.get_improvement_sequences()` | `src/api/service.py:635` | `GET /api/sequences` | → dict with `sequences`, `grouped_sequences`, `stats` |
| `APIService._get_practice_profile()` | `src/api/service.py:680` | `get_recommendations()` | `team_name, month` → `dict[str, list[str]]` (level_0 … level_3) |

## Cross-references
- **Related Use Case Skills:** `/uc-01-get-recommendations`, `/uc-02-run-backtest-validation`, `/uc-03-run-parameter-optimization`, `/uc-04-explore-improvement-sequences`, `/uc-05-view-system-statistics`
- **Related Domain Skills:** `/domain-ml` (called by service), `/domain-validation` (called by service), `/domain-data` (processor passed to service), `/domain-frontend` (consumes all endpoints)
