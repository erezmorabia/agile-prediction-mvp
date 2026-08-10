---
name: domain-frontend
description: Single-page web app with 4 tabs (Statistics, Backtest, Sequences, Recommendations). Frontend-only. Use when modifying tab layout, UI rendering, form behavior, or API call patterns in the browser.
---

# Domain: Frontend

## Summary
Frontend-only single-page application served as static files by FastAPI. Four tabs each initialize independently; all data is fetched from the FastAPI backend at runtime. No build step - plain HTML/CSS/JS.

**Visual theme:** Dark Academic Research Lab. Background `#0f0e0d` (obsidian), amber/gold accent `#f59e0b`. Fonts: Playfair Display 900 (headings), Inter (body), JetBrains Mono (numeric values). Loaded via Google Fonts `<link>` tags in `<head>`.

**CSS architecture:** Complete dark color system in `:root` variables. `--primary-500: #f59e0b` (amber) drives active tab, spinner, buttons, rec-numbers. `--gray-*` scale is warm-dark (lightest = `#1a1916`). JS-hardcoded inline backgrounds (`#f8f9fa`, `#fff3cd`) produce deliberate light "spotlight" panels - intentional. `.maturity-bar-container` has `background: var(--bg-inset) !important` to override JS inline `#e0e0e0`.

**Key CSS classes added (not in app.js):** `.header-badge`, `.header-meta`, `.header-meta-sep`, `.instrument-panel`, `.error-message`, `.debug-info`, `.per-month-results`, `.accuracy-comparison`, `.btn-ghost`, `.sequence-index`, `.modal-overlay`, `.modal-container`, `.modal-header`, `.modal-body`, `.excel-table`, `.excel-table-wrap`, `.header-about-btn`, `.modal-container--wide`, `.docs-modal-body`, `.docs-content`.

**Verdict line (Recommendations tab):** `.verdict-line` + modifier `.verdict-hit` (green), `.verdict-partial` (amber), `.verdict-miss` (red), `.verdict-nodata` (gray). Rendered by `buildVerdictLine(data)` in `app.js`, injected into `.recommendations-header` right below the month line. Shows prediction outcome in one sentence: correct count/total and which practices hit or missed.

**Button hierarchy (Backtest tab):** "Run Backtest" and "Find Optimal Config" use `btn-primary` (filled amber). "View Latest Results" and "Upload Results" use `btn-ghost` (transparent, outlined, smaller text) to de-emphasise them as secondary actions.

## Data Flows

- **App init:** `DOMContentLoaded` → `initializeTabs()` → `initializeRecommendations()`, `initializeBacktest()`, `initializeStats()`, `initializeSequences()` (each in a `setTimeout` to avoid blocking) → `loadTeamsWithTimeout()` → `GET /api/teams` → populates team dropdown
- **Recommendations flow:** team-select `change` → `GET /api/teams/{team}/months` → populates month dropdown → button enables → click → `POST /api/recommendations` → renders recommendation cards, practice profile, validation section
- **Backtest flow:** "Run Backtest" click → `POST /api/backtest` with config from form → renders overall metrics + per-month table
- **Optimization flow:** "Find Optimal Config" click → `POST /api/optimize` → cancel button appears → on response renders optimal config + all results table
- **Statistics flow:** auto-loaded on app init (default landing tab) via seeded `loadedTabs.add('stats'); loadStatistics()` in `initializeTabs()` → `GET /api/stats` → renders dataset summary, data completeness section, practice definitions
- **Data completeness section:** headline shows "Overall completeness: X%" (computed as `(total_observations * num_practices - total_missing) / (total_observations * num_practices)`). If one practice accounts for ≥80% of missing values an outlier note appears: "X% of missing values come from a single practice (Name); all others ≤ Y%". Practice list shows "not recorded in N of M months" (from `Object.keys(info.by_month).length` vs `data.num_months`) instead of raw counts.
- **Sequences flow:** tab click triggers lazy fetch → `GET /api/sequences` → renders grouped transition list
- **Example data modal flow:** "See Example Dataset" button (Statistics tab) → `openExampleModal()` → `GET /api/example-data` (FileResponse, serves raw Excel) → SheetJS parses ArrayBuffer → renders scrollable `.excel-table` in modal overlay. Max 100 rows displayed. `closeExampleModal()` triggered by ×, Escape, or clicking backdrop.
- **About / docs modal flow:** "About" button (header, top-right, absolute positioned) → `openAboutModal()` → `GET /api/docs` (PlainTextResponse, serves `PROJECT_DOCUMENTATION.md`) → `marked.parse()` renders Markdown → injects into `.docs-content` div inside `.docs-modal-body`. Markdown rendered via `marked.js` CDN (v15). Cached after first load (`_aboutLoaded` flag). `closeAboutModal()` triggered by ×, Escape, or clicking backdrop. `.modal-container--wide` caps width at 860px.

## Domain Validation Rules and Business Logic

- Team dropdown only shows teams returned by `GET /api/teams`; month dropdown only shows months returned by `GET /api/teams/{team}/months` (month 3+ filtering happens server-side)
- Cancel button for optimization shown only while a POST /api/optimize request is pending
- Accuracy displayed as "-" when `accuracy` is `null` in the response (no improvements in validation window)
- Teams loaded with timeout guard (`loadTeamsWithTimeout`) - if the fetch exceeds the timeout, a fallback error state is shown and other tabs remain usable
- Per-month results table column headers each carry a `tip()` tooltip (ⓘ icon, pure-CSS bubble) explaining what the column measures and any exclusion rules (e.g. why teams with zero improvements are excluded)
- **Tooltip clipping fix:** `.results-table` has `overflow: visible` (no clipping). Tables are wrapped in `<div class="table-outer">` which holds `overflow: hidden; border-radius; box-shadow` for corner rounding - never put `overflow: hidden` directly on `.results-table` or tooltip bubbles will be clipped
- **Backtest accuracy-comparison box bottom section:** Split into two flex columns separated by a 1px vertical rule — left: Improvement Gap (additive %, color-coded), right: Improvement Factor (multiplicative ×, same color-code). Both computed locally from `modelAccuracy / randomBaseline`; guard against `randomBaseline === 0` by showing `—`.
- **Overall Accuracy = macro average, not raw ratio:** `overall_accuracy` from the API is `sum(per_month_accuracy) / num_months` — each month weighted equally. The raw ratio `correct_predictions / total_predictions` is smaller because it weights months by team count. The metric card shows both: the macro average (headline) and the raw ratio below it (e.g. "raw ratio: 41.5% (59 ÷ 142)"). Do not change the tooltip to say "correct ÷ total" — that is the raw ratio, not what is displayed.

## Cross-references
- **Related Use Case Skills:** `/uc-01-get-recommendations`, `/uc-02-run-backtest-validation`, `/uc-03-run-parameter-optimization`, `/uc-04-explore-improvement-sequences`, `/uc-05-view-system-statistics`
- **Related Domain Skills:** `/domain-api` (all endpoints consumed here)
