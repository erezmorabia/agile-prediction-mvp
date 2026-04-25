---
name: domain-frontend
description: Single-page web app with 4 tabs (Statistics, Backtest, Sequences, Recommendations). Frontend-only. Use when modifying tab layout, UI rendering, form behavior, or API call patterns in the browser.
---

# Domain: Frontend

## Summary
Frontend-only single-page application served as static files by FastAPI. Four tabs each initialize independently; all data is fetched from the FastAPI backend at runtime. No build step — plain HTML/CSS/JS.

**Visual theme:** Dark Academic Research Lab. Background `#0f0e0d` (obsidian), amber/gold accent `#f59e0b`. Fonts: Playfair Display 900 (headings), Inter (body), JetBrains Mono (numeric values). Loaded via Google Fonts `<link>` tags in `<head>`.

**CSS architecture:** Complete dark color system in `:root` variables. `--primary-500: #f59e0b` (amber) drives active tab, spinner, buttons, rec-numbers. `--gray-*` scale is warm-dark (lightest = `#1a1916`). JS-hardcoded inline backgrounds (`#f8f9fa`, `#fff3cd`) produce deliberate light "spotlight" panels — intentional. `.maturity-bar-container` has `background: var(--bg-inset) !important` to override JS inline `#e0e0e0`.

**Key CSS classes added (not in app.js):** `.header-badge`, `.header-meta`, `.header-meta-sep`, `.instrument-panel`, `.error-message`, `.debug-info`, `.per-month-results`, `.accuracy-comparison`.

## Data Flows

- **App init:** `DOMContentLoaded` → `initializeTabs()` → `initializeRecommendations()`, `initializeBacktest()`, `initializeStats()`, `initializeSequences()` (each in a `setTimeout` to avoid blocking) → `loadTeamsWithTimeout()` → `GET /api/teams` → populates team dropdown
- **Recommendations flow:** team-select `change` → `GET /api/teams/{team}/months` → populates month dropdown → button enables → click → `POST /api/recommendations` → renders recommendation cards, practice profile, validation section
- **Backtest flow:** "Run Backtest" click → `POST /api/backtest` with config from form → renders overall metrics + per-month table
- **Optimization flow:** "Find Optimal Config" click → `POST /api/optimize` → cancel button appears → on response renders optimal config + all results table
- **Statistics flow:** auto-loaded on app init (default landing tab) via seeded `loadedTabs.add('stats'); loadStatistics()` in `initializeTabs()` → `GET /api/stats` → renders dataset summary, similarity stats, missing values, practice definitions
- **Sequences flow:** tab click triggers lazy fetch → `GET /api/sequences` → renders grouped transition list

## Domain Validation Rules and Business Logic

- Team dropdown only shows teams returned by `GET /api/teams`; month dropdown only shows months returned by `GET /api/teams/{team}/months` (month 3+ filtering happens server-side)
- Cancel button for optimization shown only while a POST /api/optimize request is pending
- Accuracy displayed as "—" when `accuracy` is `null` in the response (no improvements in validation window)
- Teams loaded with timeout guard (`loadTeamsWithTimeout`) — if the fetch exceeds the timeout, a fallback error state is shown and other tabs remain usable

## Cross-references
- **Related Use Case Skills:** `/uc-01-get-recommendations`, `/uc-02-run-backtest-validation`, `/uc-03-run-parameter-optimization`, `/uc-04-explore-improvement-sequences`, `/uc-05-view-system-statistics`
- **Related Domain Skills:** `/domain-api` (all endpoints consumed here)
