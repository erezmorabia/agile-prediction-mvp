---
name: domain-frontend
description: Single-page web app with 4 tabs (Statistics, Backtest, Sequences, Recommendations). Frontend-only. Use when modifying tab layout, UI rendering, form behavior, or API call patterns in the browser.
---

# Domain: Frontend

## Summary
Frontend-only single-page application served as static files by FastAPI. Four tabs each initialize independently; all data is fetched from the FastAPI backend at runtime. No build step - plain HTML/CSS/JS. The Backtest tab has no configuration form and no optimizer controls - the global monthly policy (see `/domain-ml`) is the only configuration authority for both the live recommendation flow and the backtest.

**CSS architecture:** Color system driven by CSS custom properties in `:root` (`--primary-500`, `--gray-*` scale, etc. - see `style.css`). Some JS-hardcoded inline backgrounds intentionally break from the dark theme to produce light "spotlight" panels - not a bug. `.maturity-bar-container` needs an `!important` override to win over one such JS inline style.

**Key CSS classes added (not in app.js):** `.header-badge`, `.header-meta`, `.header-meta-sep`, `.instrument-panel`, `.error-message`, `.debug-info`, `.per-month-results`, `.accuracy-comparison`, `.btn-ghost`, `.sequence-index`, `.modal-overlay`, `.modal-container`, `.modal-header`, `.modal-body`, `.excel-table`, `.excel-table-wrap`, `.header-about-btn`, `.modal-container--wide`, `.docs-modal-body`, `.docs-content`.

**Verdict line (Recommendations tab):** `.verdict-line` + modifier `.verdict-hit` (green), `.verdict-partial` (amber), `.verdict-miss` (red), `.verdict-nodata` (gray). Rendered by `buildVerdictLine(data)` in `app.js`, injected into `.recommendations-header` right below the month line. Shows prediction outcome in one sentence: correct count/total and which practices hit or missed.

**Policy audit box (Recommendations tab):** `.policy-audit-box`, rendered by `policyAuditHtml(policy)` right below the recommendations header. Shows the selected policy's similarity/sequence/popularity weights, popularity recency, peer pool (or "N/A (bootstrap policy)"), the fixed 2-snapshot component windows, and how many completed prior months it was selected from. The same shape (`policy_summary()` dict) is rendered per-month in the Backtest tab's per-month table.

**Button hierarchy (Backtest tab):** "Run Backtest Validation" uses `btn-primary` (filled amber); it is disabled while a run is in progress.

## Data Flows

- **App init:** `DOMContentLoaded` → `initializeTabs()` → `initializeRecommendations()`, `initializeBacktest()`, `initializeStats()`, `initializeSequences()` (each in a `setTimeout` to avoid blocking) → `loadTeamsWithTimeout()` → `GET /api/teams` → populates team dropdown
- **Recommendations flow:** team-select `change` → `GET /api/teams/{team}/months` → populates each option as `Current: baseline → Predict: prediction` → button enables → click → `POST /api/recommendations` (`{team, month: prediction, top_n: 2}`, no other params) → renders recommendation cards, policy audit box, practice profile, validation section. If the response carries a `message` (team has fewer than two candidate practices), that message is shown instead of recommendation cards
- **Backtest flow:** "Run Backtest Validation" click → `POST /api/backtest` (no body) → renders a Primary Results section, a separately-labelled Sensitivity Results section, and a per-month table tagging each row Primary/Sensitivity with its selected policy
- **Statistics flow:** auto-loaded on app init (default landing tab) via seeded `loadedTabs.add('stats'); loadStatistics()` in `initializeTabs()` → `GET /api/stats` → renders dataset summary, data completeness section, practice definitions
- **Data completeness section:** headline shows "Overall completeness: X%" (computed as `(total_observations * num_practices - total_missing) / (total_observations * num_practices)`). If one practice accounts for ≥80% of missing values an outlier note appears: "X% of missing values come from a single practice (Name); all others ≤ Y%". Practice list shows "not recorded in N of M months" (from `Object.keys(info.by_month).length` vs `data.num_months`) instead of raw counts.
- **Sequences flow:** tab click triggers lazy fetch → `GET /api/sequences` → renders grouped transition list (all-history, independent of whatever month `PolicyEngine` last gated the shared mapper to - see `/domain-api`)
- **Example data modal flow:** "See Example Dataset" button (Statistics tab) → `openExampleModal()` → `GET /api/example-data` (FileResponse, serves raw Excel) → SheetJS parses ArrayBuffer → renders scrollable `.excel-table` in modal overlay. Max 100 rows displayed. `closeExampleModal()` triggered by ×, Escape, or clicking backdrop.
- **About / docs modal flow:** "About" button (header, top-right, absolute positioned) → `openAboutModal()` → `GET /api/docs` (PlainTextResponse, serves `PROJECT_DOCUMENTATION.md`) → `marked.parse()` renders Markdown → injects into `.docs-content` div inside `.docs-modal-body`. Markdown rendered via `marked.js` CDN (v15). Cached after first load (`_aboutLoaded` flag). `closeAboutModal()` triggered by ×, Escape, or clicking backdrop. `.modal-container--wide` caps width at 860px.

## Domain Validation Rules and Business Logic

- Team dropdown only shows teams returned by `GET /api/teams`; the month dropdown receives valid prediction months from `GET /api/teams/{team}/months` and uses the team metadata to display the immediately preceding team snapshot as the current month
- `top_n` is hardcoded to `2` in `api.js`'s `getRecommendations()` - there is no user-facing control for it in the web interface
- Accuracy displayed as "-" when `accuracy` is `null` in the response (no improvements in validation window); the same "not enough completed months" fallback appears in `renderScopeSummary()` when a backtest scope's `months_included` is 0
- Teams loaded with timeout guard (`loadTeamsWithTimeout`) - if the fetch exceeds the timeout, a fallback error state is shown and other tabs remain usable
- Per-month results table column headers each carry a `tip()` tooltip (ⓘ icon, pure-CSS bubble) explaining what the column measures and any exclusion rules
- **Results-table scrolling:** `.results-table` has `overflow: visible` (no clipping) and a readable minimum width. Its `.table-outer` wrapper owns the border radius, shadow, and horizontal scrolling on narrow screens.
- **Backtest accuracy-comparison boxes:** one box per scope (Primary/Sensitivity) for Blend vs Random and Blend vs Time-Aware Popularity, using `formatFactor()` to render `—` when a baseline is zero or the scope has no qualifying months

## Cross-references
- **Related Use Case Skills:** `/uc-01-get-recommendations`, `/uc-02-run-backtest-validation`, `/uc-04-explore-improvement-sequences`, `/uc-05-view-system-statistics`
- **Related Domain Skills:** `/domain-api` (all endpoints consumed here), `/domain-ml` (the policy audit shape rendered here comes from `policy_summary()`)
