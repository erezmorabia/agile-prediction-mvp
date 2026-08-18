---
name: domain-api
description: FastAPI app factory, route handlers, APIService orchestration, Pydantic models, startup. Use when modifying endpoints, request/response shapes, service layer logic, or startup initialization.
---

# Domain: API

## Summary
`APIService` wraps all ML and validation components for HTTP consumption. `create_routes()` registers 10 endpoints on a shared `APIRouter`; `create_app()` mounts static files and wires routes. The backtest (not an optimizer - that was removed entirely) runs in a `ThreadPoolExecutor` so the event loop stays free for cancel requests.

## Data Flows

- **App startup:** `create_app(service)` → mounts `web/static` at `/static` → serves `web/index.html` at `/` → calls `create_routes(service)` and includes the router
- **Request lifecycle:** HTTP request → route handler (async) → `APIService` method → ML/validation component → Pydantic model → JSON response
- **Backtest async pattern:** `POST /api/backtest` calls `loop.run_in_executor(_executor, service.run_backtest)` with `ThreadPoolExecutor(max_workers=1)` — allows a concurrent `POST /api/backtest/cancel` to be processed by the same event loop. This executor and pattern were repointed from the deleted optimizer's `/api/optimize`, not newly added
- **Recommendations:** `POST /api/recommendations` takes only `team`, `month`, and `top_n` (pinned to `Literal[2]` - a request for any other value fails Pydantic validation, `extra="forbid"` rejects unknown fields like the old `k_similar`); the response carries `selected_policy` (the month's audit record from `policy_summary()`), `no_similar_teams_found`, and `message` (set when the team has fewer than two candidate practices)
- **Practice definitions:** `APIService.__init__()` tries `data/raw/practice_level_definitions.xlsx` then falls back to legacy filename; included in `GET /api/stats` response if loaded
- **Missing values:** `web_main.py` sets `service.missing_values_details` after startup; surfaced via `GET /api/stats`
- **Sequences tab freshness:** `APIService.get_improvement_sequences()` calls `sequence_mapper.learn_sequences()` (all-history) before reading, so it never shows whatever month-gated state `PolicyEngine` last left on the shared mapper

## External API Patterns

- All endpoints under `/api/` prefix; static files at `/static/`; SPA shell at `/`
- Backtest endpoint uses `asyncio.get_event_loop().run_in_executor()` — do not convert to `await asyncio.to_thread()` without testing cancel concurrency
- `GET /api/example-data` — serves `data/raw/combined_dataset.xlsx` as a `FileResponse` (used by the Statistics tab "See Example Dataset" modal)
- `GET /api/docs` — serves `docs/PROJECT_DOCUMENTATION.md` as a `PlainTextResponse` (used by the "About" modal in the header)
- **Removed entirely:** `POST /api/optimize`, `POST /api/optimize/cancel`, `GET /api/optimize/latest`, and the `OptimizationRequest`/`OptimizationResult`/`OptimizationResponse` models. Do not re-add a static all-history configuration search - the global monthly policy (`/domain-ml`) is the only configuration authority for the primary flow and its backtest

## Backend Functions

| Class / Method | File | Called from | Key params / returns |
|---|---|---|---|
| `create_app()` | `src/api/main.py` | `web_main.py` | `service: APIService` → `FastAPI` app instance |
| `create_routes()` | `src/api/routes.py` | `create_app()` | `service: APIService` → `APIRouter` with all 10 routes registered |
| `APIService.get_all_teams()` | `src/api/service.py` | `GET /api/teams` | → `list[dict]` sorted by num_months desc |
| `APIService.get_teams_with_improvements()` | `src/api/service.py` | `GET /api/teams/with-improvements` | → `list[dict]` (team, month, improvements), filtered to `PolicyEngine.prediction_months()` |
| `APIService.get_team_months()` | `src/api/service.py` | `GET /api/teams/{team_name}/months` | `team_name` → `list[int]` (valid prediction months with a usable baseline) or `None` |
| `APIService.get_recommendations()` | `src/api/service.py` | `POST /api/recommendations` | `team_name, month` → dict with `recommendations`, `validation`, `practice_profile`, `selected_policy`, `no_similar_teams_found`, `message` |
| `APIService.run_backtest()` | `src/api/service.py` | `POST /api/backtest` (via executor) | no params → `{per_month_results, primary, sensitivity, cancelled}` |
| `APIService.cancel_backtest()` | `src/api/service.py` | `POST /api/backtest/cancel` | → `backtest_engine.cancel()` |
| `APIService.get_system_stats()` | `src/api/service.py` | `GET /api/stats` | → dict with team/practice/month counts, definitions, missing values |
| `APIService.get_improvement_sequences()` | `src/api/service.py` | `GET /api/sequences` | → dict with `sequences`, `grouped_sequences`, `stats` |
| `APIService._get_practice_profile()` | `src/api/service.py` | `get_recommendations()` | `team_name, month` → `dict[str, list[str]]` (level_0 … level_3) |

## Cross-references
- **Related Use Case Skills:** `/uc-01-get-recommendations`, `/uc-02-run-backtest-validation`, `/uc-04-explore-improvement-sequences`, `/uc-05-view-system-statistics`
- **Related Domain Skills:** `/domain-ml` (called by service), `/domain-validation` (called by service), `/domain-data` (processor passed to service), `/domain-frontend` (consumes all endpoints)
